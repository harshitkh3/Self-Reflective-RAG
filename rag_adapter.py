"""
RAG Adapter connecting the Self-RAG LangGraph pipeline in complete_graph.py
to the PopQA evaluation benchmark in popqa_selfrag_eval.py.
"""
from typing import Any, Dict
from complete_graph import build_app

# Cache compiled app instances by retriever id to avoid re-compiling StateGraph on every question
_app_cache: Dict[int, Any] = {}


def get_app(retriever):
    """Retrieve or compile the Self-RAG LangGraph app for a given retriever."""
    retriever_key = id(retriever)
    if retriever_key not in _app_cache:
        _app_cache[retriever_key] = build_app(retriever=retriever)
    return _app_cache[retriever_key]


def run_rag(question: str, retriever) -> dict:
    """
    Executes the Self-RAG pipeline on the given question with the provided retriever.
    Returns diagnostic metrics expected by popqa_selfrag_eval.py.
    """
    app = get_app(retriever)
    state = {
        "question": question,
        "docs": [],
        "relevant_docs": [],
        "context": "",
        "answer": "",
        "rewrite_tries": 0,
        "retries": 0,
        "issup": "",
        "evidence": [],
        "isuse": "",
        "use_reason": "",
        "retrieval_query": "",
        "first_answer": None,
        "num_retrievals": 0,
    }

    out = app.invoke(state)

    docs = out.get("docs") or []
    return {
        "answer": out.get("answer", ""),
        "final_answer": out.get("answer", ""),
        "docs": docs,
        "retrieved_docs": docs,
        "relevant_docs": out.get("relevant_docs", []),
        "need_retrieval": out.get("need_retrieval"),
        "rewrite_tries": out.get("rewrite_tries", 0),
        "retries": out.get("retries", 0),
        "issup": out.get("issup"),
        "isuse": out.get("isuse"),
        "first_answer": out.get("first_answer"),
        "num_retrievals": out.get("num_retrievals", 1 if docs else 0),
    }
