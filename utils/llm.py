import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "PLACEHOLDER_KEY"

primary = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    api_key=api_key,
    max_retries=5,
)

fallback = ChatOpenRouter(
    model='openrouter/free',
    temperature=0
)
llm = primary.with_fallbacks([fallback])
