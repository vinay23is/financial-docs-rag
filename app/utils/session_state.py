import os
import shutil
from utils.prepare_vectordb import get_vectorstore

SEC_FILINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sec_filings")

PRELOADED_FILINGS = {
    "AAPL_10K_Summary.pdf": "Apple Inc. (AAPL) — FY2025 10-K Summary",
    "GOOGL_10K_Summary.pdf": "Alphabet Inc. (GOOGL) — FY2024 10-K Summary",
    "TSLA_10K_Summary.pdf": "Tesla, Inc. (TSLA) — FY2025 10-K Summary",
}

def ensure_sec_filings_in_docs():
    """Copy bundled SEC filing PDFs into the docs/ folder on first run."""
    os.makedirs("docs", exist_ok=True)
    copied = []
    for filename in PRELOADED_FILINGS:
        src = os.path.join(SEC_FILINGS_DIR, filename)
        dst = os.path.join("docs", filename)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied.append(filename)
    return copied

def initialize_session_state_variables(st):
    ensure_sec_filings_in_docs()
    upload_docs = os.listdir("docs")

    variables = ["chat_history", "uploaded_pdfs", "processed_documents",
                 "vectordb", "previous_upload_docs_length"]
    for var in variables:
        if var not in st.session_state:
            if var == "processed_documents":
                st.session_state.processed_documents = upload_docs
            elif var == "vectordb":
                st.session_state.vectordb = get_vectorstore(upload_docs, from_session_state=True)
            elif var == "previous_upload_docs_length":
                st.session_state.previous_upload_docs_length = len(upload_docs)
            else:
                st.session_state[var] = []
