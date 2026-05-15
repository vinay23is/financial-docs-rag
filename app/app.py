import streamlit as st
import os
from utils.save_docs import save_docs_to_vectordb
from utils.session_state import initialize_session_state_variables, PRELOADED_FILINGS
from utils.prepare_vectordb import get_vectorstore
from utils.chatbot import chat

CUSTOM_CSS = """
<style>
/* Main background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #1b2d3e 100%);
    border-right: 1px solid #2a4a6a;
}
/* Header */
.sec-header {
    background: linear-gradient(135deg, #1B3A6B 0%, #0d2a4a 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #2E6AA3;
    box-shadow: 0 4px 20px rgba(27, 58, 107, 0.4);
}
.sec-header h1 {
    color: #FFFFFF;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.sec-header p {
    color: #7EB8F7;
    font-size: 0.9rem;
    margin: 0.3rem 0 0;
}
/* Company badge */
.company-badge {
    display: inline-block;
    background: rgba(46, 125, 50, 0.15);
    border: 1px solid #2E7D32;
    color: #81C784;
    padding: 0.25rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 0.2rem 0.2rem 0.2rem 0;
}
/* Sample questions */
.sample-q-box {
    background: rgba(27, 58, 107, 0.2);
    border: 1px solid #2E6AA3;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 1rem;
}
.sample-q-box p {
    color: #7EB8F7;
    font-size: 0.82rem;
    margin: 0.15rem 0;
    cursor: pointer;
}
.sample-q-box p::before { content: "💬 "; }
/* Info box */
.info-box {
    background: rgba(27, 58, 107, 0.15);
    border-left: 4px solid #2E6AA3;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    color: #7EB8F7;
    font-size: 0.88rem;
}
/* Chat messages */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    margin-bottom: 0.5rem;
}
/* Sidebar text */
[data-testid="stSidebar"] * {
    color: #C8D8E8 !important;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #7EB8F7 !important;
}
/* Upload area */
[data-testid="stFileUploader"] {
    background: rgba(27, 58, 107, 0.1);
    border-radius: 8px;
}
/* Spinner */
[data-testid="stSpinner"] { color: #7EB8F7; }
</style>
"""

SAMPLE_QUESTIONS = [
    "What was Apple's total revenue in its most recent fiscal year?",
    "How does Tesla's net income compare to Alphabet's?",
    "What are the main risk factors for Tesla?",
    "What percentage of Apple's revenue comes from Services?",
    "What is Alphabet's Google Cloud revenue growth story?",
    "How many employees does each company have?",
    "What did Tesla's MD&A say about vehicle delivery growth?",
    "Compare the R&D spending of Apple, Google, and Tesla.",
]

COMPANY_INFO = {
    "AAPL_10K_Summary.pdf": {"label": "Apple (AAPL)", "emoji": "🍎", "fy": "FY2025"},
    "GOOGL_10K_Summary.pdf": {"label": "Alphabet/Google (GOOGL)", "emoji": "🔍", "fy": "FY2024"},
    "TSLA_10K_Summary.pdf": {"label": "Tesla (TSLA)", "emoji": "⚡", "fy": "FY2025"},
}


class SECFilingAnalyzer:
    def __init__(self):
        os.makedirs("docs", exist_ok=True)
        st.set_page_config(
            page_title="SEC Filing Analyzer",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
        initialize_session_state_variables(st)
        self.docs_files = st.session_state.processed_documents

    def _render_sidebar(self, upload_docs):
        with st.sidebar:
            st.markdown("## 📊 SEC Filing Analyzer")
            st.markdown("---")

            # Pre-loaded companies
            st.markdown("### 🏢 Pre-loaded Companies")
            for filename, info in COMPANY_INFO.items():
                status = "✅" if filename in upload_docs else "⏳"
                st.markdown(
                    f"{status} {info['emoji']} **{info['label']}** — {info['fy']}",
                    unsafe_allow_html=True,
                )
            st.markdown("---")

            # User uploads
            st.markdown("### 📁 Add Your Own Filings")
            st.caption("Upload additional SEC PDF filings to expand the knowledge base.")
            pdf_docs = st.file_uploader(
                "Select PDF(s)",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
            if pdf_docs:
                save_docs_to_vectordb(pdf_docs, upload_docs)

            if len(upload_docs) > len(PRELOADED_FILINGS):
                extra = [f for f in upload_docs if f not in PRELOADED_FILINGS]
                st.markdown("**Your uploaded files:**")
                for f in extra:
                    st.markdown(f"📄 {f}")

            st.markdown("---")
            st.markdown("### 💡 Sample Questions")
            for q in SAMPLE_QUESTIONS[:4]:
                st.markdown(f"<p style='font-size:0.8rem;color:#7EB8F7;'>• {q}</p>",
                            unsafe_allow_html=True)

            st.markdown("---")
            st.caption(
                "Data sourced from SEC EDGAR public filings. "
                "Not investment advice. "
                "[View on GitHub](https://github.com/vinay23is/financial-docs-rag)"
            )

    def run(self):
        upload_docs = os.listdir("docs")

        self._render_sidebar(upload_docs)

        # Header
        st.markdown("""
        <div class="sec-header">
            <h1>📊 SEC Filing Analyzer</h1>
            <p>Ask questions about Apple, Alphabet (Google), and Tesla's annual financial filings powered by RAG + Gemini AI</p>
        </div>
        """, unsafe_allow_html=True)

        # Company badges
        badges_html = " ".join(
            f'<span class="company-badge">{info["emoji"]} {info["label"]} {info["fy"]}</span>'
            for info in COMPANY_INFO.values()
        )
        st.markdown(f'<div style="margin-bottom:1rem;">{badges_html}</div>',
                    unsafe_allow_html=True)

        # Update vectordb if new docs added
        if len(upload_docs) > st.session_state.previous_upload_docs_length:
            st.session_state.vectordb = get_vectorstore(upload_docs, from_session_state=True)
            st.session_state.previous_upload_docs_length = len(upload_docs)

        # Chat area
        if self.docs_files or st.session_state.uploaded_pdfs:
            st.session_state.chat_history = chat(
                st.session_state.chat_history,
                st.session_state.vectordb,
            )
            if not st.session_state.chat_history:
                self._render_welcome()
        else:
            self._render_welcome()

    def _render_welcome(self):
        st.markdown("""
        <div class="info-box">
            <strong>Welcome!</strong> The SEC filings for Apple, Alphabet, and Tesla are pre-loaded.
            Start chatting below — no upload needed. You can also add your own SEC PDFs in the sidebar.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### 💬 Try asking:")
        cols = st.columns(2)
        for i, q in enumerate(SAMPLE_QUESTIONS):
            with cols[i % 2]:
                st.markdown(
                    f"<div class='sample-q-box'><p>{q}</p></div>",
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    app = SECFilingAnalyzer()
    app.run()
