import os
import streamlit as st
from utils.prepare_vectordb import get_vectorstore

def save_docs_to_vectordb(pdf_docs, existing_docs):
    new_files = [pdf for pdf in pdf_docs if pdf.name not in existing_docs]
    if not new_files:
        return
    new_names = [pdf.name for pdf in new_files]
    if st.button("Process uploaded files"):
        with st.spinner("Processing your documents..."):
            for pdf in new_files:
                path = os.path.join("docs", pdf.name)
                with open(path, "wb") as f:
                    f.write(pdf.getvalue())
            st.session_state.uploaded_pdfs.extend(new_files)
            get_vectorstore(new_names)
            st.success(f"Added {len(new_files)} file(s) to the knowledge base.")
