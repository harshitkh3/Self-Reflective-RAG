import sys
from graph import app

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    question = "Do NexaAI plans include a free trial? If yes, how many days?"
    print(f"Question: {question}\n")

    result = app.invoke(
        {
            "question": question,
            "docs": [],
            "relevant_docs": [],
            "context": "",
            "answer": "",
            "issup": "",
            "evidence": [],
        }
    )

    print("--- Execution Results ---")
    print("Need Retrieval :", result.get("need_retrieval"))
    print("Retrieved Docs :", len(result.get("docs", [])))
    print("Relevant Docs  :", len(result.get("relevant_docs", [])))
    print("IsSUP Decision :", result.get("issup"))
    print("Evidence       :", result.get("evidence"))
    print("Final Answer   :", result.get("answer"))


if __name__ == "__main__":
    main()
