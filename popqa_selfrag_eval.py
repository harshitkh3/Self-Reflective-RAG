"""
PopQA evaluation for a custom Self-Reflective RAG.

Paper-inspired setup:
- Filter PopQA to long-tail subjects with s_pop < 100.
- Use paper-style answer matching: any normalized gold answer occurs in generation.
- Build a separate Wikipedia-backed Chroma collection.
- Report diagnostic retrieval/reflection metrics only when the graph adapter exposes them.

This is NOT an exact reproduction of the original paper: original SELF-RAG used
its provided offline-retrieved contexts and its own model/inference implementation.

Install:
  pip install datasets requests tqdm langchain-core langchain-text-splitters langchain-chroma langchain-ollama
  ollama pull mxbai-embed-large

Build index:
  python popqa_selfrag_eval.py build --limit 100
  python popqa_selfrag_eval.py build --limit 1399

Evaluate (requires rag_adapter.py; see rag_adapter_template.py):
  python popqa_selfrag_eval.py evaluate --limit 100 --adapter rag_adapter:run_rag
"""

import argparse, ast, importlib, json, re, time, sys
from collections import Counter
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

script_dir = str(Path(__file__).parent.resolve())
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import requests
from datasets import load_dataset
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

DATASET_ID = "akariasai/PopQA"
CHROMA_DIR = "./chroma_popqa"
COLLECTION = "popqa_wikipedia"
EMBED_MODEL = "mxbai-embed-large"
WIKI_API = "https://en.wikipedia.org/w/api.php"
CACHE = Path("./popqa_wikipedia_cache")


def load_longtail(limit=1399, seed=42):
    ds = load_dataset(DATASET_ID, split="test")
    if "s_pop" not in ds.column_names:
        raise ValueError(f"Missing s_pop column. Columns: {ds.column_names}")
    ds = ds.filter(lambda r: r["s_pop"] is not None and float(r["s_pop"]) < 100)
    ds = ds.shuffle(seed=seed)
    if limit is not None:
        ds = ds.select(range(min(limit, len(ds))))
    return ds


def gold_list(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if value is None:
        return []
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    return [str(value).strip()] if str(value).strip() else []


def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", s).split())


def paper_match(prediction, gold_answers):
    """Paper-inspired match metric, not strict exact match."""
    p = norm(prediction)
    return int(bool(p) and any(norm(g) and norm(g) in p for g in gold_answers))


def token_f1(prediction, gold):
    p, g = norm(prediction).split(), norm(gold).split()
    if not p or not g:
        return float(p == g)
    common = sum((Counter(p) & Counter(g)).values())
    if not common:
        return 0.0
    precision, recall = common / len(p), common / len(g)
    return 2 * precision * recall / (precision + recall)


def best_f1(prediction, golds):
    return max((token_f1(prediction, g) for g in golds), default=0.0)


def fetch_article(title, session):
    CACHE.mkdir(exist_ok=True, parents=True)
    cache_path = CACHE / (re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:150] + ".json")
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("text"):
                return cached
        except Exception:
            pass
    try:
        r = session.get(WIKI_API, params={
            "action": "query", "format": "json", "formatversion": "2",
            "prop": "extracts", "explaintext": "1", "redirects": "1", "titles": title
        }, timeout=30)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return None
        page = pages[0]
        text = (page.get("extract") or "").strip()
        if not text:
            return None
        item = {"title": page.get("title", title), "pageid": page.get("pageid"), "text": text}
        cache_path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
        return item
    except requests.RequestException as e:
        print(f"[WARN] {title}: {e}")
        return None
    finally:
        time.sleep(0.1)


def build_index(limit=1399, seed=42):
    ds = load_longtail(limit, seed)
    print(f"Selected long-tail questions: {len(ds)}")
    titles = {}
    for row in ds:
        title = row.get("s_wiki_title")
        if title:
            titles.setdefault(str(title), {"subj": row.get("subj"), "subj_id": row.get("subj_id")})

    session = requests.Session()
    session.headers.update({"User-Agent": "PopQA-SelfReflectiveRAG/1.0 (research evaluation)"})
    documents = []
    for title, meta in tqdm(titles.items(), desc="Fetching Wikipedia"):
        article = fetch_article(title, session)
        if article:
            documents.append(Document(page_content=article["text"], metadata={
                "source": "wikipedia", "wiki_title": article["title"],
                "wiki_pageid": article.get("pageid"), "popqa_subject": meta["subj"],
                "subj_id": meta["subj_id"]
            }))
    if not documents:
        raise RuntimeError("No Wikipedia pages fetched. Check internet and s_wiki_title.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600, chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    print(f"Fetched {len(documents)} articles; created {len(chunks)} chunks.")

    embed = OllamaEmbeddings(model=EMBED_MODEL)
    store = Chroma(collection_name=COLLECTION, embedding_function=embed, persist_directory=CHROMA_DIR)
    try:
        store.delete_collection()
    except Exception:
        pass
    store = Chroma(collection_name=COLLECTION, embedding_function=embed, persist_directory=CHROMA_DIR)
    for start in tqdm(range(0, len(chunks), 64), desc="Embedding/indexing"):
        store.add_documents(chunks[start:start+64])
    print(f"Index ready: {CHROMA_DIR}, collection={COLLECTION}")


def get_retriever(k=5):
    if not Path(CHROMA_DIR).exists():
        raise FileNotFoundError(
            f"Chroma directory '{CHROMA_DIR}' not found. "
            "Please build the index first using: python popqa_selfrag_eval.py build --limit <N>"
        )
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=OllamaEmbeddings(model=EMBED_MODEL),
        persist_directory=CHROMA_DIR
    )
    return store.as_retriever(search_kwargs={"k": k})


def load_adapter(spec):
    if ":" not in spec:
        raise ValueError("Use --adapter module:function, e.g. rag_adapter:run_rag")
    mod, func = spec.split(":", 1)
    return getattr(importlib.import_module(mod), func)


def as_docs(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def title_of(doc):
    return str((getattr(doc, "metadata", {}) or {}).get("wiki_title", "")).strip().casefold()


def evaluate(limit=1399, seed=42, adapter="rag_adapter:run_rag", k=5, output="popqa_eval_results.json"):
    ds = load_longtail(limit, seed)
    run_rag = load_adapter(adapter)
    retriever = get_retriever(k)
    rows, retrieval_decisions, support_decisions, ranks = [], [], [], []
    total_retrievals = 0
    rescue_seen = rescue_initial_wrong = rescued = 0

    for i, item in enumerate(tqdm(ds, desc="PopQA evaluation")):
        golds = gold_list(item.get("possible_answers"))
        try:
            out = run_rag(item["question"], retriever)
            if not isinstance(out, dict):
                raise TypeError("Adapter must return a dict")
            answer = str(out.get("answer") or out.get("final_answer") or "")
            match = paper_match(answer, golds)
            f1 = best_f1(answer, golds)
            docs = as_docs(out.get("docs") or out.get("retrieved_docs"))
            expected = str(item.get("s_wiki_title") or "").strip().casefold()
            found_ranks = [j+1 for j, d in enumerate(docs) if title_of(d) == expected and expected]
            rank = min(found_ranks) if found_ranks else None
            ranks.append(rank)

            if out.get("need_retrieval") is not None:
                retrieval_decisions.append(bool(out["need_retrieval"]))
            if out.get("issup") is not None:
                s = str(out["issup"]).lower()
                support_decisions.append(
                    any(x in s for x in ("fully supported", "supported", "yes", "true"))
                    and not any(x in s for x in ("not supported", "unsupported", "no support", "false"))
                )
            total_retrievals += int(out.get("num_retrievals", 1 if docs else 0) or 0)

            first = out.get("first_answer")
            rescue = None
            if first is not None:
                rescue_seen += 1
                if not paper_match(str(first), golds):
                    rescue_initial_wrong += 1
                    rescue = bool(match)
                    rescued += int(bool(match))

            rows.append({
                "popqa_id": item.get("id"), "question": item["question"],
                "subject": item.get("subj"), "relation": item.get("prop"),
                "wiki_title": item.get("s_wiki_title"), "s_pop": item.get("s_pop"),
                "gold_answers": golds, "prediction": answer,
                "paper_style_match": match, "token_f1_diagnostic": f1,
                "retrieved_titles": [getattr(d, "metadata", {}).get("wiki_title", "") for d in docs],
                "retrieved_doc_count": len(docs), "subject_article_rank": rank,
                "need_retrieval": out.get("need_retrieval"),
                "rewrite_tries": out.get("rewrite_tries", 0),
                "support_retries": out.get("retries", 0), "issup": out.get("issup"),
                "isuse": out.get("isuse"), "first_answer": first,
                "reflection_rescued": rescue, "error": None
            })
            print(f"{i+1}/{len(ds)} match={match}: {item['question']} -> {answer[:100]}")
        except Exception as e:
            rows.append({"popqa_id": item.get("id"), "question": item["question"],
                         "gold_answers": golds, "prediction": "", "paper_style_match": 0,
                         "token_f1_diagnostic": 0.0, "error": f"{type(e).__name__}: {e}"})
            print(f"[ERROR] {item['question']}: {e}")

    ok = [r for r in rows if r.get("error") is None]
    n = len(ok)
    summary = {
        "subset": "PopQA long-tail: s_pop < 100",
        "questions_attempted": len(rows), "successful_runs": n,
        "paper_style_popqa_accuracy_percent": round(100*sum(r["paper_style_match"] for r in ok)/n, 3) if n else None,
        "mean_token_f1_diagnostic": round(sum(r["token_f1_diagnostic"] for r in ok)/n, 4) if n else None,
        "retrieval_rate_percent": round(100*sum(retrieval_decisions)/len(retrieval_decisions), 3) if retrieval_decisions else None,
        "answer_support_rate_percent": round(100*sum(support_decisions)/len(support_decisions), 3) if support_decisions else None,
        "subject_article_hit_at_k_percent": round(100*sum(r is not None for r in ranks)/len(ranks), 3) if ranks else None,
        "subject_article_mrr_at_k": round(sum(1/r if r else 0 for r in ranks)/len(ranks), 4) if ranks else None,
        "average_retrievals_per_question": round(total_retrievals/n, 3) if n else None,
        "reflection_rescue_rate_percent": round(100*rescued/rescue_initial_wrong, 3) if rescue_initial_wrong else None,
        "rescue_observations_with_first_answer": rescue_seen,
        "metric_notes": {
            "paper_style_accuracy": "Any normalized gold answer string appears in generated answer; approximates the paper's match metric.",
            "subject_article_hit_mrr": "Title-match proxy, not evidence-level recall; retrieved docs need wiki_title metadata.",
            "support_rate": "Only computed if adapter returns issup.",
            "retrieval_rate": "Only computed if adapter returns need_retrieval.",
            "rescue_rate": "Only computed for adapter outputs containing first_answer."
        }
    }
    Path(output).write_text(json.dumps({"summary": summary, "results": rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Detailed results saved to {output}")


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd", required=True)
    b = subs.add_parser("build")
    b.add_argument("--limit", type=int, default=1399)
    b.add_argument("--seed", type=int, default=42)
    e = subs.add_parser("evaluate")
    e.add_argument("--limit", type=int, default=1399)
    e.add_argument("--seed", type=int, default=42)
    e.add_argument("--adapter", default="rag_adapter:run_rag")
    e.add_argument("--k", type=int, default=5)
    e.add_argument("--output", default="popqa_eval_results.json")
    args = parser.parse_args()
    if args.cmd == "build":
        build_index(args.limit, args.seed)
    else:
        evaluate(args.limit, args.seed, args.adapter, args.k, args.output)


if __name__ == "__main__":
    main()
