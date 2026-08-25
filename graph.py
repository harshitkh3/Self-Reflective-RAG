from typing import List, Literal, TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END

from nodes import (
    decide_retrieval,
    route_after_decide,
    generate_direct,
    retrieve,
    is_relevant,
    route_after_relevance,
    generate_from_context,
    no_answer_found,
    is_sup,
)

# -----------------------------
# Graph State
# -----------------------------
class State(TypedDict):
    question: str
    need_retrieval: bool
    docs: List[Document]
    relevant_docs: List[Document]
    context: str
    answer: str

    # Post-generation verification
    issup: Literal["fully_supported", "partially_supported", "no_support"]
    evidence: List[str]


# -----------------------------
# Build graph
# -----------------------------
def create_graph() -> StateGraph:
    g = StateGraph(State)

    g.add_node("decide_retrieval", decide_retrieval)
    g.add_node("generate_direct", generate_direct)
    g.add_node("retrieve", retrieve)

    g.add_node("is_relevant", is_relevant)
    g.add_node("generate_from_context", generate_from_context)
    g.add_node("no_answer_found", no_answer_found)

    g.add_node("is_sup", is_sup)

    g.add_edge(START, "decide_retrieval")

    g.add_conditional_edges(
        "decide_retrieval",
        route_after_decide,
        {"generate_direct": "generate_direct", "retrieve": "retrieve"},
    )

    g.add_edge("generate_direct", END)

    g.add_edge("retrieve", "is_relevant")

    g.add_conditional_edges(
        "is_relevant",
        route_after_relevance,
        {
            "generate_from_context": "generate_from_context",
            "no_answer_found": "no_answer_found",
        },
    )

    # If no answer found, end
    g.add_edge("no_answer_found", END)

    # If generated from context, verify with IsSUP loop
    g.add_edge("generate_from_context", "is_sup")
    g.add_edge("is_sup", END)

    return g


# Initialize and compile the state graph
workflow = create_graph()
app = workflow.compile()

if __name__ == "__main__":
    initial_input = {
        "question": "Do NexaAI plans include a free trial? If yes, how many days?",
        "docs": [],
        "relevant_docs": [],
        "context": "",
        "answer": "",
        "issup": "",
        "evidence": [],
    }
    result = app.invoke(initial_input)
    print("need_retrieval:", result.get("need_retrieval"))
    print("#docs:", len(result.get("docs", [])))
    print("#relevant_docs:", len(result.get("relevant_docs", [])))
    print("issup:", result.get("issup"))
    print("evidence:", result.get("evidence"))
    print("answer:", result.get("answer"))
