import os
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from graph import app as rag_app
from tools.retriever import DOCS_DIR, reset_retriever

app = FastAPI(title="Self-Reflective RAG Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    need_retrieval: bool
    retrieved_docs_count: int
    relevant_docs_count: int
    issup: str
    evidence: List[str]
    answer: str
    context: str
    retrieved_docs: List[dict]
    relevant_docs: List[dict]


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.get("/api/health")
async def health_check():
    has_gemini = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "model": "gemini-3.5-flash-lite",
        "embeddings": "gemini-embedding-001",
        "gemini_api_key_configured": has_gemini,
    }


@app.get("/api/documents")
async def list_documents():
    docs = []
    if DOCS_DIR.exists():
        for f in DOCS_DIR.glob("*.pdf"):
            stat = f.stat()
            docs.append(
                {
                    "name": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": stat.st_mtime,
                }
            )
    return {"documents": sorted(docs, key=lambda x: x["name"])}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    destination = DOCS_DIR / file.filename

    with open(destination, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    reset_retriever()
    return {"status": "success", "filename": file.filename}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    file_path = DOCS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_path.unlink()
    reset_retriever()
    return {"status": "deleted", "filename": filename}


@app.post("/api/reindex")
async def reindex_documents():
    reset_retriever()
    return {"status": "reindexed"}


@app.post("/api/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        initial_input = {
            "question": question,
            "docs": [],
            "relevant_docs": [],
            "context": "",
            "answer": "",
            "issup": "",
            "evidence": [],
        }

        result = rag_app.invoke(initial_input)

        raw_docs = result.get("docs", [])
        raw_rel_docs = result.get("relevant_docs", [])

        serializable_docs = [
            {
                "content": d.page_content,
                "source": Path(d.metadata.get("source", "Document")).name,
                "page": d.metadata.get("page", 0) + 1,
            }
            for d in raw_docs
        ]

        serializable_rel_docs = [
            {
                "content": d.page_content,
                "source": Path(d.metadata.get("source", "Document")).name,
                "page": d.metadata.get("page", 0) + 1,
            }
            for d in raw_rel_docs
        ]

        answer = result.get("answer", "")
        if isinstance(answer, list):
            answer = "".join(
                [b.get("text", "") if isinstance(b, dict) else str(b) for b in answer]
            )

        return QueryResponse(
            question=question,
            need_retrieval=bool(result.get("need_retrieval", False)),
            retrieved_docs_count=len(raw_docs),
            relevant_docs_count=len(raw_rel_docs),
            issup=str(result.get("issup", "unknown")),
            evidence=result.get("evidence", []) or [],
            answer=str(answer),
            context=str(result.get("context", "")),
            retrieved_docs=serializable_docs,
            relevant_docs=serializable_rel_docs,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn

    print("Starting Self-Reflective RAG Web App on http://localhost:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
