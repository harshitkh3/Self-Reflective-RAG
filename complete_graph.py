import os
import sys
import time
from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langgraph.graph import StateGraph, START, END

load_dotenv()

# Google Cloud LLM instance
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project="ai-api-2335",
    location="us-central1",
    temperature=0
)

# -----------------------------
# Lazy Default Retriever
# -----------------------------
_default_retriever = None

def get_company_retriever(k: int = 4):
    """Lazily load or initialize the company knowledge base vector store."""
    global _default_retriever
    if _default_retriever is not None:
        return _default_retriever

    persist_directory = "./chroma_db"
    collection_name = "company_open_knowledge_base"
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")

    if os.path.exists(persist_directory):
        try:
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings,
                collection_name=collection_name
            )
            if vector_store._collection.count() > 0:
                _default_retriever = vector_store.as_retriever(search_kwargs={"k": k})
                return _default_retriever
        except Exception as e:
            print(f"Loading existing collection failed ({e}), re-indexing...")

    # Load and index PDF documents if collection not found or empty
    pdf_paths = [
        "./documents/Company_Policies.pdf",
        "./documents/Company_Profile.pdf",
        "./documents/Product_and_Pricing.pdf"
    ]
    raw_docs = []
    for p in pdf_paths:
        if os.path.exists(p):
            raw_docs.extend(PyPDFLoader(p).load())

    if not raw_docs:
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name=collection_name
        )
        _default_retriever = vector_store.as_retriever(search_kwargs={"k": k})
        return _default_retriever

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=150)
    raw_chunks = text_splitter.split_documents(raw_docs)

    formatted_chunks = []
    for i, chunk in enumerate(raw_chunks):
        source_file = os.path.basename(chunk.metadata.get("source", "Unknown_Document"))
        page_num = chunk.metadata.get("page", 0) + 1
        doc_title = os.path.splitext(source_file)[0].replace("_", " ")
        clean_text = chunk.page_content.strip()

        open_knowledge_content = (
            f"[KNOWLEDGE SOURCE: {doc_title}] [FILE: {source_file}] [PAGE: {page_num}]\n"
            f"--------------------------------------------------\n"
            f"{clean_text}"
        )
        enriched_doc = Document(
            page_content=open_knowledge_content,
            metadata={
                **chunk.metadata,
                "source_file": source_file,
                "doc_title": doc_title,
                "page_number": page_num,
                "chunk_id": f"{source_file}_p{page_num}_chunk{i+1}",
                "format": "open_knowledge_standard"
            }
        )
        formatted_chunks.append(enriched_doc)

    vector_store = Chroma.from_documents(
        documents=formatted_chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name=collection_name
    )
    _default_retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return _default_retriever


# -----------------------------
# State Declaration
# -----------------------------
class State(TypedDict, total=False):
    question: str
    need_retrieval: bool
    docs: List[Document]
    answer: str
    context: str
    relevant_docs: List[Document]
    issup: Literal["fully_supported", "partially_supported", "no_support"]
    evidence: List[str]
    retries: int
    isuse: Literal['useful', 'not_useful']
    use_reason: str
    retrieval_query: str
    rewrite_tries: int
    first_answer: Optional[str]
    num_retrievals: int


# -----------------------------
# Node: Decide Retrieval
# -----------------------------
class RetrieveDecision(BaseModel):
    should_retrieve: bool = Field(description='True if external documents are needed to answer reliably, else False')

decide_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You decide whether retrieval is needed.\n"
            "Return JSON that matches this schema:\n"
            "{{'should_retrieve': boolean}}\n\n"
            "Guidelines:\n"
            "- should_retrieve=True if answering requires specific facts, citations, or info likely not in the model.\n"
            "- should_retrieve=False for general explanations, definitions, or reasoning that doesn't need sources.\n"
            "- If unsure, choose True."
        ),
        ("human", "Question: {question}"),
    ]
)

def decide_retrieval(state: State):
    try:
        should_retrieve_llm = llm.with_structured_output(RetrieveDecision)
        chain = decide_retrieval_prompt | should_retrieve_llm
        decision = chain.invoke({'question': state["question"]})
        should_retrieve = decision.should_retrieve if decision else True
    except Exception as e:
        print(f"decide_retrieval warning: {e}. Defaulting to True.")
        should_retrieve = True
    return {'need_retrieval': should_retrieve}

def route_after_decide(state: State) -> Literal['direct', 'retrieve']:
    if state.get('need_retrieval', True):
        return 'retrieve'
    return 'direct'


# -----------------------------
# Node: Direct Answer
# -----------------------------
def direct_ans(state: State):
    direct_ans_prompt = ChatPromptTemplate.from_messages([
        ('system', "You are an AI assistant. Answer this question concisely and factually from your knowledge base and training data. DO NOT assume access to external documents. If you are unsure or the answer requires specific sources, say:\n'I don't know based on my general knowledge.'"),
        ('human', '{question}')
    ])
    ans = llm.invoke(direct_ans_prompt.format_messages(question=state["question"]))
    ans_text = ans.content if hasattr(ans, "content") else str(ans)
    first_ans = state.get("first_answer") or ans_text
    return {"answer": ans_text, "first_answer": first_ans}


# -----------------------------
# Node: Document Relevance Filter
# -----------------------------
class DocGrade(BaseModel):
    doc_index: int = Field(description="0-based index of the document being evaluated.")
    is_relevant: bool = Field(description="True if relevant, else False.")

class AllDocsRelevance(BaseModel):
    grades: List[DocGrade] = Field(description="Relevance decisions for each document index.")

all_docs_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are evaluating the relevance of multiple retrieved documents to a user query at a TOPIC level.\n"
        "Return JSON listing whether each document is relevant.\n"
        "A document is relevant if it relates to the topic or entity in the query.\n"
        "If unsure, mark is_relevant=True.",
    ),
    ("human", "Query: {question}\n\nDocuments:\n{formatted_docs}"),
])

all_relevance_chain = all_docs_prompt | llm.with_structured_output(AllDocsRelevance)

def is_relevant(state: State):
    docs = state.get("docs", [])
    if not docs:
        return {"relevant_docs": []}

    active_query = state.get("retrieval_query") or state.get("question", "")
    formatted_docs = "\n\n".join(
        f"--- [Doc {i}] ---\n{doc.page_content}" for i, doc in enumerate(docs)
    )

    try:
        decision = all_relevance_chain.invoke({
            "question": active_query,
            "formatted_docs": formatted_docs,
        })
        if decision and decision.grades:
            relevant_indices = {
                g.doc_index for g in decision.grades if g.is_relevant and g.doc_index >= 0
            }
            relevant_docs = [doc for i, doc in enumerate(docs) if i in relevant_indices]
        else:
            relevant_docs = docs
    except Exception as e:
        print(f"Relevance grading error: {e}. Defaulting to all retrieved docs.")
        relevant_docs = docs

    return {"relevant_docs": relevant_docs}

def route_after_relevance(state: State) -> Literal["generate_from_context", "no_relevant_docs"]:
    if state.get("relevant_docs") and len(state["relevant_docs"]) > 0:
        return "generate_from_context"
    return "no_relevant_docs"


# -----------------------------
# Node: RAG Generation
# -----------------------------
rag_prompt = ChatPromptTemplate.from_messages([
    ('system', """You are an expert factual RAG assistant.
Answer the question directly and concisely based strictly on the given context. DO NOT assume or extrapolate information beyond what is stated in the context.
If the context does not contain enough information to answer the question, say "Not enough information found".
Do not use Markdown bold formatting. Never enclose words or phrases in double asterisks (**word**). Format all output in clean, plain text without bolding, italics, or markdown headers."""),
    ('human', """Question : {question}
Context : {context}""")
])

def generate_from_context(state: State):
    context = "\n\n---\n\n".join(
        [d.page_content for d in state.get("relevant_docs", [])]
    ).strip()

    if not context:
        ans_text = "No relevant document found."
        first_ans = state.get("first_answer") or ans_text
        return {"answer": ans_text, "context": "", "first_answer": first_ans}

    try:
        out = llm.invoke(
            rag_prompt.format_messages(
                question=state["question"],
                context=context
            )
        )
        ans_text = out.content if hasattr(out, "content") else str(out)
    except Exception as e:
        print(f"Generation Error: {e}")
        ans_text = "An error occurred during generation."

    first_ans = state.get("first_answer") or ans_text
    return {"answer": ans_text, "context": context, "first_answer": first_ans}

def no_relevant_docs(state: State):
    ans_text = "No relevant document found."
    first_ans = state.get("first_answer") or ans_text
    return {
        "answer": ans_text,
        "context": "",
        "first_answer": first_ans,
        "issup": "no_support",
        "evidence": []
    }


# -----------------------------
# Node: Support Verification (IsSUP)
# -----------------------------
class issup(BaseModel):
    issup: Literal['fully_supported', 'partially_supported', 'no_support'] = Field(
        description="Must be one of 'fully_supported', 'partially_supported', or 'no_support'"
    )
    evidence: List[str] = Field(default_factory=list, description="Up to 3 short direct quotes from CONTEXT that support the supported parts.")

issup_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are verifying whether the ANSWER is supported by the CONTEXT.\n"
            "Return JSON with keys: issup, evidence.\n"
            "issup must be one of: fully_supported, partially_supported, no_support.\n\n"
            "How to decide issup:\n"
            "- fully_supported:\n"
            "  Every meaningful claim is explicitly supported by CONTEXT, and the ANSWER does NOT introduce\n"
            "  unsupported claims or speculation.\n\n"
            "- partially_supported:\n"
            "  The core facts are supported, BUT the ANSWER includes extraneous phrasing or details\n"
            "  not explicitly stated in CONTEXT.\n\n"
            "- no_support:\n"
            "  The key claims are not supported by CONTEXT.\n\n"
            "Rules:\n"
            "- If you see ANY unsupported claims, choose partially_supported or no_support.\n"
            "- Evidence: include up to 3 short direct quotes from CONTEXT that support the supported parts.\n"
            "- Do not use outside knowledge."
        ),
        (
            "human",
            "Question:\n{question}\n\n"
            "Answer:\n{answer}\n\n"
            "Context:\n{context}\n"
        ),
    ]
)

issup_llm = llm.with_structured_output(issup)
issup_chain = issup_prompt | issup_llm

def is_sup(state: State):
    context = state.get("context", "")
    if not context:
        return {"issup": "no_support", "evidence": []}

    try:
        decision = issup_chain.invoke({
            "question": state.get("question", ""),
            "answer": state.get("answer", ""),
            "context": context,
        })
        if not decision:
            return {"issup": "no_support", "evidence": []}
        return {"issup": decision.issup, "evidence": decision.evidence}
    except Exception as e:
        print(f"is_sup error: {e}. Defaulting to fully_supported.")
        return {"issup": "fully_supported", "evidence": []}

MAX_RETRIES = 2

def route_after_sup(state: State):
    if state.get('issup') == 'fully_supported':
        return "accept_answer"
    if state.get('retries', 0) >= MAX_RETRIES:
        return "accept_answer"
    return "revise_answer"

def accept_answer(state: State):
    return {}


# -----------------------------
# Node: Revise Answer
# -----------------------------
revise_prompt = ChatPromptTemplate.from_messages([
    ('system',
     "You are a STRICT reviser.\n\n"
     "Revise the ANSWER so that every single claim is directly and strictly supported by the CONTEXT.\n"
     "Rules:\n"
     "- Use ONLY facts stated in the CONTEXT.\n"
     "- Remove any unsupported claims, assumptions, or conversational fluff.\n"
     "- Keep the revised answer concise and factual.\n"),
    (
        "human",
        "Question:\n{question}\n\n"
        "Current Answer:\n{answer}\n\n"
        "CONTEXT:\n{context}"
    ),
])

def revise_answer(state: State):
    try:
        out = llm.invoke(
            revise_prompt.format_messages(
                question=state["question"],
                answer=state.get("answer", ""),
                context=state.get("context", ""),
            )
        )
        ans_text = out.content if hasattr(out, "content") else str(out)
    except Exception as e:
        print(f"Revise error: {e}")
        ans_text = state.get("answer", "")
    return {
        "answer": ans_text,
        "retries": state.get("retries", 0) + 1,
    }


# -----------------------------
# Node: Usefulness Check (IsUSE)
# -----------------------------
class IsUSEDecision(BaseModel):
    isuse: Literal['useful', 'not_useful']
    reason: str = Field(..., description="Short reason in 1 line.")

isuse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are judging USEFULNESS of the ANSWER for the QUESTION.\n\n"
            "Goal:\n"
            "- Decide if the answer actually addresses what the user asked.\n\n"
            "Return JSON with keys: isuse, reason.\n"
            "isuse must be one of: useful, not_useful.\n\n"
            "Rules:\n"
            "- useful: The answer directly answers the question or provides the requested specific info.\n"
            "- not_useful: The answer is generic, off-topic, or only gives related background without answering.\n"
            "- Do NOT use outside knowledge.\n"
            "- Do NOT re-check grounding (IsSUP already did that). Only check: 'Did we answer the question?'\n"
            "- Keep reason to 1 short line."
        ),
        (
            "human",
            "Question:\n{question}\n\nAnswer:\n{answer}"
        ),
    ]
)

isuse_llm = llm.with_structured_output(IsUSEDecision)

def is_use(state: State):
    ans = state.get("answer", "")
    if "no relevant document found" in ans.lower() or "not enough information" in ans.lower():
        return {"isuse": "not_useful", "use_reason": "No relevant document or information found"}

    try:
        decision = isuse_llm.invoke(
            isuse_prompt.format_messages(
                question=state["question"],
                answer=ans,
            )
        )
        if decision:
            return {"isuse": decision.isuse, "use_reason": decision.reason}
    except Exception as e:
        print(f"is_use error: {e}")
    return {"isuse": "useful", "use_reason": "default fallback"}

MAX_REWRITE_TRIES = 2

def route_after_isuse(state: State) -> Literal["END", "rewrite_question", "no_answer_found"]:
    if state.get("isuse") == "useful":
        return "END"

    if state.get("rewrite_tries", 0) >= MAX_REWRITE_TRIES:
        return "no_answer_found"

    return "rewrite_question"


# -----------------------------
# Node: Rewrite Query
# -----------------------------
class RewriteDecision(BaseModel):
    retrieval_query: str = Field(
        ...,
        description="Rewritten query optimized for vector retrieval."
    )

rewrite_for_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's QUESTION into an effective search query optimized for vector retrieval.\n\n"
            "Rules:\n"
            "- Focus on the core subject, entity, and information need.\n"
            "- Add high-signal keywords or synonyms that are likely to appear in reference documents.\n"
            "- Keep it concise (3-12 words).\n"
            "- Remove conversational filler words.\n"
            "- Do NOT answer the question.\n"
            "- Output JSON with key: retrieval_query\n\n"
            "Examples:\n"
            "Q: 'Who directed Inception?'\n"
            "-> {{'retrieval_query': 'Inception film director Christopher Nolan'}}\n\n"
            "Q: 'What is the refund policy?'\n"
            "-> {{'retrieval_query': 'refund policy cancellation timeline charges'}}"
        ),
        (
            "human",
            "QUESTION:\n{question}\n\n"
            "Previous retrieval query:\n{retrieval_query}\n\n"
            "Answer (if any):\n{answer}"
        ),
    ]
)

rewrite_llm = llm.with_structured_output(RewriteDecision)

def rewrite_question(state: State):
    try:
        decision = rewrite_llm.invoke(
            rewrite_for_retrieval_prompt.format_messages(
                question=state["question"],
                retrieval_query=state.get("retrieval_query", ""),
                answer=state.get("answer", ""),
            )
        )
        new_query = decision.retrieval_query if decision else state["question"]
    except Exception as e:
        print(f"rewrite error: {e}")
        new_query = state["question"]

    return {
        "retrieval_query": new_query,
        "rewrite_tries": state.get("rewrite_tries", 0) + 1,
        "docs": [],
        "relevant_docs": [],
        "context": "",
    }

def no_answer_found(state: State):
    return {"answer": "No answer found.", "context": ""}


# -----------------------------
# Build Graph / App Factory
# -----------------------------
def build_graph(retriever=None) -> StateGraph:
    """Build the Self-RAG LangGraph with the provided or default retriever."""
    active_retriever = retriever if retriever is not None else get_company_retriever()

    def retrieve(state: State):
        q = state.get("retrieval_query") or state["question"]
        docs = active_retriever.invoke(q)
        return {
            "docs": docs,
            "num_retrievals": state.get("num_retrievals", 0) + 1
        }

    g = StateGraph(State)

    # Nodes
    g.add_node('decide_retrieval', decide_retrieval)
    g.add_node('direct_ans', direct_ans)
    g.add_node('retrieve', retrieve)
    g.add_node('is_relevant', is_relevant)
    g.add_node('generate_from_context', generate_from_context)
    g.add_node('no_relevant_docs', no_relevant_docs)
    g.add_node('is_sup', is_sup)
    g.add_node('revise_answer', revise_answer)
    g.add_node('accept_answer', accept_answer)
    g.add_node('is_use', is_use)
    g.add_node('no_answer_found', no_answer_found)
    g.add_node('rewrite_question', rewrite_question)

    # Edges
    g.add_edge(START, 'decide_retrieval')
    g.add_conditional_edges(
        'decide_retrieval',
        route_after_decide,
        {
            'retrieve': 'retrieve',
            'direct': 'direct_ans'
        }
    )
    g.add_edge('direct_ans', END)

    g.add_edge('retrieve', 'is_relevant')
    g.add_conditional_edges(
        'is_relevant',
        route_after_relevance,
        {
            'generate_from_context': 'generate_from_context',
            'no_relevant_docs': 'no_relevant_docs'
        }
    )
    g.add_edge('no_relevant_docs', 'is_use')

    g.add_edge('generate_from_context', 'is_sup')
    g.add_conditional_edges(
        'is_sup',
        route_after_sup,
        {
            'accept_answer': 'accept_answer',
            'revise_answer': 'revise_answer'
        }
    )
    g.add_edge('revise_answer', 'is_sup')
    g.add_edge('accept_answer', 'is_use')

    g.add_conditional_edges(
        'is_use',
        route_after_isuse,
        {
            'END': END,
            'rewrite_question': 'rewrite_question',
            'no_answer_found': 'no_answer_found'
        }
    )
    g.add_edge('rewrite_question', 'retrieve')
    g.add_edge('no_answer_found', END)

    return g


def build_app(retriever=None):
    """Compile and return the Self-RAG LangGraph runnable."""
    graph = build_graph(retriever=retriever)
    return graph.compile()


# -----------------------------
# Standalone Execution / Testing
# -----------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("Building Self-RAG pipeline with default company document retriever...")
    app = build_app()

    test_questions = [
        "What is the refund policy of NexaAI",
        "Describe NexaAI's company culture.",
    ]

    for q in test_questions:
        print(f"\n--- Testing Query: {q} ---")
        state = {
            "question": q,
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
        res = app.invoke(state)
        print("Need Retrieval:", res.get("need_retrieval"))
        print("Total retrieved docs:", len(res.get("docs", [])))
        print("Relevant docs:", len(res.get("relevant_docs", [])))
        print("IsSUP:", res.get("issup"))
        print("IsUSE:", res.get("isuse"))
        print("Final Answer:\n", res.get("answer"))
