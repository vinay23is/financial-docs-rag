"""
Lambda handler for financial-docs RAG.

Environment variables:
  GOOGLE_API_KEY   – Gemini API key
  S3_BUCKET        – bucket where the FAISS snapshot lives
  S3_PREFIX        – S3 key prefix (default: "vectordb/")
"""

import json
import logging
import os
import tarfile
import tempfile

import boto3
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SYSTEM_PROMPT = """You are an expert financial analyst specializing in SEC annual filings (10-K reports).
You have access to 10-K filing summaries for Apple (AAPL), Alphabet/Google (GOOGL), and Tesla (TSLA),
as well as any additional documents the user has uploaded.

Your job is to answer questions accurately using the retrieved content from these filings.
- Cite specific figures (revenue, net income, EPS, etc.) when available.
- If a question cannot be answered from the provided context, say so clearly — do not invent numbers.
- When comparing companies, be precise about which fiscal year each figure refers to.

Answer the question using this context from the SEC filings:
{context}"""

# Cached across warm invocations
_vectorstore = None


def _download_faiss_index() -> str:
    bucket = os.environ["S3_BUCKET"]
    prefix = os.environ.get("S3_PREFIX", "vectordb").rstrip("/")
    s3_key = f"{prefix}/faiss_index.tar.gz"

    local_tar = os.path.join(tempfile.gettempdir(), "faiss_index.tar.gz")
    local_dir = os.path.join(tempfile.gettempdir(), "faiss_index")

    logger.info("Downloading FAISS index from s3://%s/%s", bucket, s3_key)
    boto3.client("s3").download_file(bucket, s3_key, local_tar)

    os.makedirs(local_dir, exist_ok=True)
    with tarfile.open(local_tar, "r:gz") as tar:
        tar.extractall(tempfile.gettempdir())

    os.remove(local_tar)
    logger.info("FAISS index extracted to %s", local_dir)
    return local_dir


def _get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    local_dir = _download_faiss_index()
    embedding = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.environ["GOOGLE_API_KEY"],
        task_type="retrieval_document",
    )
    _vectorstore = FAISS.load_local(
        local_dir,
        embedding,
        allow_dangerous_deserialization=True,
    )
    return _vectorstore


def _build_chat_history(raw_history: list) -> list:
    messages = []
    for entry in raw_history or []:
        role = entry.get("role", "")
        content = entry.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def handler(event, context):
    body = event
    if "body" in event:
        raw = event["body"]
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})

    query = (body.get("query") or "").strip()
    if not query:
        return _response(400, {"error": "Missing required field: query"})

    raw_history = body.get("chat_history", [])
    k = int(body.get("k", 5))

    try:
        vectorstore = _get_vectorstore()
    except Exception as exc:
        logger.exception("Failed to load vector store")
        return _response(500, {"error": f"Vector store unavailable: {exc}"})

    docs = vectorstore.similarity_search(query, k=k)
    context_text = "\n\n".join(doc.page_content for doc in docs)

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.1,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "context": context_text,
        "chat_history": _build_chat_history(raw_history),
        "input": query,
    })

    sources = []
    seen = set()
    for doc in docs:
        meta = doc.metadata or {}
        src = os.path.basename(meta.get("source", "Unknown"))
        page = int(meta.get("page", 0))
        key = (src, page)
        if key not in seen:
            seen.add(key)
            sources.append({"source": src, "page": page + 1, "snippet": doc.page_content[:1500]})

    return _response(200, {"answer": answer, "sources": sources})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
