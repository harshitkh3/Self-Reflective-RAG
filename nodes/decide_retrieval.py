from typing import Any, Dict, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from utils.llm import llm


class RetrieveDecision(BaseModel):
    should_retrieve: bool = Field(
        ...,
        description="True if external documents are needed to answer reliably, else False.",
    )


decide_retrieval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You decide whether retrieval is needed.\n"
            "Return JSON with key: should_retrieve (boolean).\n\n"
            "Guidelines:\n"
            "- should_retrieve=True if answering requires specific facts from company documents.\n"
            "- should_retrieve=False for general explanations/definitions.\n"
            "- If unsure, choose True.",
        ),
        ("human", "Question: {question}"),
    ]
)

should_retrieve_llm = llm.with_structured_output(RetrieveDecision)


def decide_retrieval(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        decision: RetrieveDecision = should_retrieve_llm.invoke(
            decide_retrieval_prompt.format_messages(question=state["question"])
        )
        return {"need_retrieval": decision.should_retrieve}
    except Exception:
        # Fallback: if unsure, retrieve documents
        return {"need_retrieval": True}


def route_after_decide(state: Dict[str, Any]) -> Literal["generate_direct", "retrieve"]:
    return "retrieve" if state.get("need_retrieval", True) else "generate_direct"
