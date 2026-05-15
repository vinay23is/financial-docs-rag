import streamlit as st
import os
from utils.save_docs import save_docs_to_vectordb
from utils.session_state import initialize_session_state_variables, PRELOADED_FILINGS
from utils.prepare_vectordb import get_vectorstore
from utils.chatbot import chat

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
[data-testid="stAppViewContainer"] {
    background: #F0F4F8;
}
[data-testid="stMain"] {
    background: #F0F4F8;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] h1 {
    color: #F8FAFC !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
}
[data-testid="stSidebar"] .sidebar-section-title {
    color: #94A3B8 !important;
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px dashed #334155 !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #94A3B8 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
    margin: 0.6rem 0 !important;
}

/* ── Main content area ── */
[data-testid="stMainBlockContainer"] {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}

/* ── Hero header ── */
.hero {
    background: linear-gradient(135deg, #1E3A5F 0%, #1A56DB 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(26, 86, 219, 0.25);
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.55);
    margin-bottom: 0.5rem;
}
.hero h1 {
    font-size: 1.9rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0 0 0.5rem;
    letter-spacing: -0.5px;
    line-height: 1.2;
}
.hero p {
    font-size: 0.9rem;
    color: rgba(255,255,255,0.7);
    margin: 0;
    line-height: 1.6;
    max-width: 560px;
}
.hero-badge {
    display: inline-block;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    margin-top: 1rem;
    margin-right: 0.4rem;
}

/* ── Company cards ── */
.company-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    height: 100%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.company-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.company-card .ticker {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    margin-bottom: 0.6rem;
    display: inline-block;
}
.company-card .name {
    font-size: 0.88rem;
    font-weight: 600;
    color: #1E293B;
    margin-bottom: 0.2rem;
}
.company-card .fy {
    font-size: 0.72rem;
    color: #94A3B8;
    font-weight: 500;
}
.aapl-ticker  { background: #FEF3C7; color: #92400E; }
.googl-ticker { background: #DBEAFE; color: #1E40AF; }
.tsla-ticker  { background: #D1FAE5; color: #065F46; }

/* ── Welcome / sample Q section ── */
.welcome-box {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #1A56DB;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.2rem;
    font-size: 0.88rem;
    color: #334155;
    line-height: 1.6;
}
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #94A3B8;
    margin: 1.2rem 0 0.6rem;
}
.q-pill {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.65rem 0.9rem;
    font-size: 0.82rem;
    color: #334155;
    margin-bottom: 0.5rem;
    cursor: pointer;
    line-height: 1.4;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: border-color 0.15s, box-shadow 0.15s;
}
.q-pill:hover {
    border-color: #1A56DB;
    box-shadow: 0 2px 8px rgba(26,86,219,0.12);
    color: #1A56DB;
}
.q-pill::before { content: "→  "; color: #94A3B8; font-size: 0.75rem; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 14px !important;
    padding: 0.8rem 1rem !important;
    margin-bottom: 0.6rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: #EFF6FF !important;
    border-color: #BFDBFE !important;
}
[data-testid="stChatInput"] > div {
    background: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
}
[data-testid="stChatInput"] textarea {
    color: #1E293B !important;
    font-size: 0.9rem !important;
}

/* ── Streamlit component overrides ── */
[data-testid="stSpinner"] > div { color: #1A56DB !important; }
.stButton > button {
    background: #1A56DB !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 1.2rem !important;
}
.stButton > button:hover {
    background: #1E40AF !important;
    box-shadow: 0 4px 12px rgba(26,86,219,0.3) !important;
}

/* ── Source card in sidebar ── */
.source-item {
    background: rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 0.4rem 0.7rem;
    margin: 0.25rem 0;
    font-size: 0.78rem;
    color: #CBD5E1;
}
</style>
"""

SAMPLE_QUESTIONS = [
    "What was Apple's total revenue in its most recent fiscal year?",
    "How does Tesla's net income compare to Alphabet's?",
    "What are the main risk factors for Tesla?",
    "What is Alphabet's Google Cloud revenue growth story?",
    "How many employees does each company have?",
    "Compare the R&D spending of Apple, Google, and Tesla.",
    "What did Tesla's MD&A say about vehicle delivery growth?",
    "What percentage of Apple's revenue comes from Services?",
]

COMPANY_INFO = {
    "AAPL_10K_Summary.pdf":  {"label": "Apple Inc.",         "ticker": "AAPL",  "emoji": "🍎", "fy": "FY2025", "cls": "aapl-ticker"},
    "GOOGL_10K_Summary.pdf": {"label": "Alphabet Inc.",      "ticker": "GOOGL", "emoji": "🔍", "fy": "FY2024", "cls": "googl-ticker"},
    "TSLA_10K_Summary.pdf":  {"label": "Tesla, Inc.",        "ticker": "TSLA",  "emoji": "⚡", "fy": "FY2025", "cls": "tsla-ticker"},
}


class SECFilingAnalyzer:
    def __init__(self):
        os.makedirs("docs", exist_ok=True)
        st.set_page_config(
            page_title="SEC Filing Analyzer",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
        initialize_session_state_variables(st)
        self.docs_files = st.session_state.processed_documents

    # ── Sidebar ─────────────────────────────────────────────────────────────
    def _render_sidebar(self, upload_docs):
        with st.sidebar:
            st.markdown(
                "<h1>📈 SEC Analyzer</h1>"
                "<p style='font-size:0.75rem;color:#64748B;margin-top:-4px;'>AI-powered 10-K filing Q&A</p>",
                unsafe_allow_html=True,
            )
            st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown("<p class='sidebar-section-title'>Loaded companies</p>", unsafe_allow_html=True)
            for filename, info in COMPANY_INFO.items():
                loaded = filename in upload_docs
                dot = "🟢" if loaded else "⚪"
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;padding:5px 0;'>"
                    f"<span style='font-size:0.65rem;'>{dot}</span>"
                    f"<span style='font-size:0.82rem;font-weight:500;color:#E2E8F0;'>{info['label']}</span>"
                    f"<span style='margin-left:auto;font-size:0.65rem;font-weight:700;color:#64748B;'>{info['ticker']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<p class='sidebar-section-title'>Upload your own filing</p>", unsafe_allow_html=True)
            pdf_docs = st.file_uploader(
                "Drop a PDF here",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
            if pdf_docs:
                save_docs_to_vectordb(pdf_docs, upload_docs)

            if len(upload_docs) > len(PRELOADED_FILINGS):
                extra = [f for f in upload_docs if f not in PRELOADED_FILINGS]
                st.markdown("<p class='sidebar-section-title' style='margin-top:0.8rem;'>Your uploads</p>", unsafe_allow_html=True)
                for f in extra:
                    st.markdown(f"<div class='source-item'>📄 {f}</div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<p class='sidebar-section-title'>Try asking</p>", unsafe_allow_html=True)
            for q in SAMPLE_QUESTIONS[:4]:
                st.markdown(
                    f"<p style='font-size:0.77rem;color:#94A3B8;padding:3px 0;line-height:1.4;'>› {q}</p>",
                    unsafe_allow_html=True,
                )

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(
                "<p style='font-size:0.7rem;color:#475569;line-height:1.6;'>"
                "Data from SEC EDGAR · Not investment advice<br>"
                "<a href='https://github.com/vinay23is/financial-docs-rag' style='color:#3B82F6;'>View on GitHub ↗</a>"
                "</p>",
                unsafe_allow_html=True,
            )

    # ── Company cards row ────────────────────────────────────────────────────
    def _render_company_cards(self):
        cols = st.columns(3)
        for col, (filename, info) in zip(cols, COMPANY_INFO.items()):
            with col:
                st.markdown(
                    f"<div class='company-card'>"
                    f"<span class='ticker {info['cls']}'>{info['ticker']}</span>"
                    f"<div class='name'>{info['emoji']} {info['label']}</div>"
                    f"<div class='fy'>Annual Report · {info['fy']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Welcome screen ───────────────────────────────────────────────────────
    def _render_welcome(self):
        st.markdown(
            "<div class='welcome-box'>"
            "<strong>Ready to answer your questions.</strong> The SEC 10-K filings for Apple, Alphabet, and Tesla "
            "are pre-loaded — no upload needed. Ask anything about their financials, risks, strategy, or segment performance."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<p class='section-label'>Suggested questions</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        for i, q in enumerate(SAMPLE_QUESTIONS):
            with (col1 if i % 2 == 0 else col2):
                st.markdown(f"<div class='q-pill'>{q}</div>", unsafe_allow_html=True)

    # ── Main run ─────────────────────────────────────────────────────────────
    def run(self):
        upload_docs = os.listdir("docs")
        self._render_sidebar(upload_docs)

        # Hero header
        st.markdown(
            "<div class='hero'>"
            "<div class='hero-label'>AI · RAG · Financial Intelligence</div>"
            "<h1>SEC Filing Analyzer</h1>"
            "<p>Ask plain-English questions about Apple, Alphabet, and Tesla's annual reports. "
            "Powered by Retrieval-Augmented Generation and Gemini AI.</p>"
            "<span class='hero-badge'>🍎 AAPL FY2025</span>"
            "<span class='hero-badge'>🔍 GOOGL FY2024</span>"
            "<span class='hero-badge'>⚡ TSLA FY2025</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Company cards
        self._render_company_cards()
        st.markdown("<br>", unsafe_allow_html=True)

        # Update vectordb if new docs added
        if len(upload_docs) > st.session_state.previous_upload_docs_length:
            st.session_state.vectordb = get_vectorstore(upload_docs, from_session_state=True)
            st.session_state.previous_upload_docs_length = len(upload_docs)

        # Chat
        if self.docs_files or st.session_state.uploaded_pdfs:
            st.session_state.chat_history = chat(
                st.session_state.chat_history,
                st.session_state.vectordb,
            )
            if not st.session_state.chat_history:
                self._render_welcome()
        else:
            self._render_welcome()


if __name__ == "__main__":
    app = SECFilingAnalyzer()
    app.run()
