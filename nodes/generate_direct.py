from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from utils.llm import llm

direct_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer using only your general knowledge.\n"
            "If it requires specific company info, say:\n"
            "'I don't know based on my general knowledge.'",
        ),
        ("human", "{question}"),
    ]
)


def generate_direct(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        out = llm.invoke(
            direct_generation_prompt.format_messages(question=state["question"])
        )
        content = out.content
        if isinstance(content, list):
            content = "".join(
                [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
            )
        return {"answer": content}
    except Exception as e:
        return {"answer": f"Error generating direct answer: {e}"}
