import os
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

VECTORDB_DIR = "Vector_DB - SEC_Filings"

def _get_api_key():
    load_dotenv()
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return os.getenv("GOOGLE_API_KEY")

def extract_pdf_text(pdf_paths):
    docs = []
    for path in pdf_paths:
        docs.extend(PyPDFLoader(path).load())
    return docs

def get_text_chunks(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)

def get_vectorstore(pdf_names, from_session_state=False, base_dir="docs"):
    api_key = _get_api_key()
    embedding = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
        task_type="retrieval_document",
    )
    if from_session_state and os.path.exists(VECTORDB_DIR):
        return Chroma(persist_directory=VECTORDB_DIR, embedding_function=embedding)
    elif not from_session_state:
        pdf_paths = [os.path.join(base_dir, name) for name in pdf_names]
        docs = extract_pdf_text(pdf_paths)
        chunks = get_text_chunks(docs)
        return Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=VECTORDB_DIR,
        )
    return None
