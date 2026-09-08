from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from utils.llm import llm

rag_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a business rag chatbot.\n\n"
            "You will receive a CONTEXT block from internal company documents.\n"
            "Task:\n"
            "Answer the question based on the context\n"
            "Dont mention that you are getting a context in your answer",
        ),
        ("human", "Question:\n{question}\n\nContext:\n{context}"),
    ]
)


def generate_from_context(state: Dict[str, Any]) -> Dict[str, Any]:
    context = "\n\n---\n\n".join(
        [d.page_content for d in state.get("relevant_docs", [])]
    ).strip()
    if not context:
        return {"answer": "No answer found.", "context": ""}
    try:
        out = llm.invoke(
            rag_generation_prompt.format_messages(
                question=state["question"], context=context
            )
        )
        return {"answer": out.content, "context": context}
    except Exception as e:
        return {
            "answer": f"Error generating answer from context: {e}",
            "context": context,
        }


def no_answer_found(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"answer": "No answer found.", "context": ""}
