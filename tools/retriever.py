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

pdf_files = [
    DOCS_DIR / "Company_Policies.pdf",
    DOCS_DIR / "Company_Profile.pdf",
    DOCS_DIR / "Product_and_Pricing.pdf",
]


def load_documents() -> List:
    docs = []
    for pdf_file in pdf_files:
        if pdf_file.exists():
            loader = PyPDFLoader(str(pdf_file))
            docs.extend(loader.load())
        else:
            # Fallback to relative path
            fallback = Path("./documents") / pdf_file.name
            if fallback.exists():
                loader = PyPDFLoader(str(fallback))
                docs.extend(loader.load())
            else:
                raise FileNotFoundError(f"Document not found: {pdf_file}")
    return docs


def create_retriever():
    docs = load_documents()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
    ).split_documents(docs)

    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
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


class LazyRetriever:
    """Wrapper that initializes the retriever on first invocation."""

    def invoke(self, *args, **kwargs):
        return get_retriever().invoke(*args, **kwargs)


retriever = LazyRetriever()
