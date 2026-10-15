import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "documents"

def load_documents() -> List:
    docs = []
    target_dir = DOCS_DIR if DOCS_DIR.exists() else Path("./documents")
    pdf_files = list(target_dir.glob("*.pdf"))
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_file))
            docs.extend(loader.load())
        except Exception as e:
            print(f"Warning: could not load {pdf_file}: {e}")
    return docs


def get_embeddings():
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if google_api_key:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key,
        )
    elif openai_api_key:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_api_key)
    else:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model="mxbai-embed-large")


def create_retriever():
    docs = load_documents()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
    ).split_documents(docs)

    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
    )
    return vector_store.as_retriever(search_kwargs={"k": 4})


_retriever_instance = None


def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = create_retriever()
    return _retriever_instance


def reset_retriever():
    global _retriever_instance
    _retriever_instance = None


class LazyRetriever:
    """Wrapper that initializes the retriever on first invocation."""

    def invoke(self, *args, **kwargs):
        return get_retriever().invoke(*args, **kwargs)


retriever = LazyRetriever()
