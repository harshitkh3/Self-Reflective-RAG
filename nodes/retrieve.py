from typing import Any, Dict
from tools.retriever import retriever


def retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"docs": retriever.invoke(state["question"])}
