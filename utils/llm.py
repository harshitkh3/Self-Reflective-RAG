import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "PLACEHOLDER_KEY"

primary = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0,
    api_key=api_key,
    max_retries=5,
)

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    fallback = ChatOpenRouter(
        model="openrouter/free",
        temperature=0,
        api_key=openrouter_key,
    )
    llm = primary.with_fallbacks([fallback])
else:
    llm = primary
