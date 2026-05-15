import streamlit as st
import os
from utils.save_docs import save_docs_to_vectordb
from utils.session_state import initialize_session_state_variables, PRELOADED_FILINGS
from utils.prepare_vectordb import get_vectorstore
from utils.chatbot import chat

# ─────────────────────────────────────────────────────────────────────────────
#  Design System
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & base ─────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background: #F7F8FA !important;
}

/* ── Hide Streamlit chrome ────────────────────────── */
#MainMenu, footer, header { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stMainBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}
[data-testid="stMain"] {
    background: #F7F8FA !important;
    padding: 0 !important;
}

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0C0F17 !important;
    border-right: 1px solid #1C2030 !important;
    width: 260px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}
[data-testid="stSidebarContent"] {
    padding: 0 !important;
}
[data-testid="stSidebar"] * { color: #8B95A8 !important; }

/* ── Sidebar file uploader ────────────────────────── */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #151823 !important;
    border: 1px dashed #2A3045 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #8B95A8 !important;
    font-size: 0.78rem !important;
}
[data-testid="stSidebar"] small { display: none !important; }

/* ── Main content wrapper ─────────────────────────── */
.main-wrap {
    padding: 32px 40px 120px;
    max-width: 860px;
    margin: 0 auto;
}

/* ── Page header ──────────────────────────────────── */
.page-header {
    margin-bottom: 32px;
}
.page-header .eyebrow {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2563EB;
    margin-bottom: 8px;
}
.page-header h1 {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #0A0C10;
    line-height: 1.15;
    margin: 0 0 10px;
}
.page-header .sub {
    font-size: 0.9rem;
    color: #6B7280;
    line-height: 1.65;
    max-width: 540px;
    margin: 0;
}

/* ── Company chips row ────────────────────────────── */
.chips-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 32px;
}
.chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px 6px 8px;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1.5px solid;
    line-height: 1;
}
.chip-aapl  { background:#FFF7ED; border-color:#FED7AA; color:#9A3412; }
.chip-googl { background:#EFF6FF; border-color:#BFDBFE; color:#1D4ED8; }
.chip-tsla  { background:#F0FDF4; border-color:#BBF7D0; color:#15803D; }
.chip .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.chip-aapl  .dot { background: #F97316; }
.chip-googl .dot { background: #3B82F6; }
.chip-tsla  .dot { background: #22C55E; }

/* ── Divider ──────────────────────────────────────── */
.divider {
    height: 1px;
    background: #E5E7EB;
    margin: 24px 0;
}

/* ── Empty / welcome state ────────────────────────── */
.welcome-area {
    margin-top: 8px;
}
.welcome-title {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 4px;
}
.welcome-sub {
    font-size: 0.82rem;
    color: #9CA3AF;
    margin-bottom: 20px;
}
.q-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 8px;
}
.q-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 14px 16px;
    cursor: pointer;
    transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
}
.q-card:hover {
    border-color: #93C5FD;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08);
    transform: translateY(-1px);
}
.q-card .q-icon {
    font-size: 1.1rem;
    margin-bottom: 8px;
    display: block;
}
.q-card .q-text {
    font-size: 0.8rem;
    font-weight: 500;
    color: #374151;
    line-height: 1.45;
}

/* ── Chat messages ────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: #FFFFFF !important;
    border: 1px solid #F1F3F5 !important;
    border-radius: 14px !important;
    padding: 14px 16px !important;
    margin-bottom: 8px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}

/* ── Chat input ───────────────────────────────────── */
[data-testid="stBottom"] {
    background: linear-gradient(to top, #F7F8FA 60%, transparent) !important;
    padding: 16px 40px 24px !important;
}
[data-testid="stChatInput"] {
    max-width: 860px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"] > div {
    background: #FFFFFF !important;
    border: 1.5px solid #E5E7EB !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #93C5FD !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1), 0 2px 12px rgba(0,0,0,0.07) !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 0.88rem !important;
    color: #111827 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #9CA3AF !important;
}

/* ── Streamlit spinner ────────────────────────────── */
[data-testid="stSpinner"] > div { color: #2563EB !important; }

/* ── Buttons ──────────────────────────────────────── */
.stButton > button {
    background: #2563EB !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.1rem !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}
.stButton > button:hover {
    background: #1D4ED8 !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.25) !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar HTML
# ─────────────────────────────────────────────────────────────────────────────
SIDEBAR_HEADER = """
<div style="padding:24px 20px 16px;border-bottom:1px solid #1C2030;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
    <div style="width:28px;height:28px;background:linear-gradient(135deg,#2563EB,#7C3AED);
                border-radius:7px;display:flex;align-items:center;justify-content:center;
                font-size:14px;">📈</div>
    <span style="font-size:0.9rem;font-weight:700;color:#F1F5F9 !important;letter-spacing:-0.02em;">
      SEC Analyzer
    </span>
  </div>
  <p style="font-size:0.68rem;color:#4B5563;margin:0;padding-left:38px;">
    AI-powered 10-K Q&amp;A
  </p>
</div>
"""

def _company_row(label, ticker, fy, loaded):
    dot = (
        '<span style="width:6px;height:6px;border-radius:50%;background:#22C55E;'
        'display:inline-block;flex-shrink:0;"></span>'
        if loaded else
        '<span style="width:6px;height:6px;border-radius:50%;background:#374151;'
        'display:inline-block;flex-shrink:0;"></span>'
    )
    return (
        f'<div style="display:flex;align-items:center;gap:9px;padding:7px 12px;'
        f'border-radius:8px;margin-bottom:2px;">'
        f'{dot}'
        f'<span style="font-size:0.8rem;font-weight:500;color:#CBD5E1 !important;flex:1;">{label}</span>'
        f'<span style="font-size:0.65rem;font-weight:700;color:#4B5563 !important;'
        f'background:#1C2030;padding:2px 6px;border-radius:4px;">{ticker}</span>'
        f'</div>'
    )

SAMPLE_QUESTIONS = [
    ("💰", "What was Apple's total revenue in FY2025?"),
    ("📊", "Compare R&D spending across all three companies."),
    ("⚠️", "What are the top risk factors for Tesla?"),
    ("☁️", "What is Alphabet's Google Cloud revenue story?"),
    ("👥", "How many employees does each company have?"),
    ("📱", "What percentage of Apple's revenue is from Services?"),
    ("🚗", "What did Tesla's MD&A say about vehicle deliveries?"),
    ("💹", "How does Tesla's net income compare to Alphabet's?"),
]

COMPANY_INFO = {
    "AAPL_10K_Summary.pdf":  {"label": "Apple Inc.",    "ticker": "AAPL",  "fy": "FY2025", "chip": "chip-aapl"},
    "GOOGL_10K_Summary.pdf": {"label": "Alphabet Inc.", "ticker": "GOOGL", "fy": "FY2024", "chip": "chip-googl"},
    "TSLA_10K_Summary.pdf":  {"label": "Tesla, Inc.",   "ticker": "TSLA",  "fy": "FY2025", "chip": "chip-tsla"},
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

    # ── Sidebar ──────────────────────────────────────────────────────────────
    def _render_sidebar(self, upload_docs):
        with st.sidebar:
            st.markdown(SIDEBAR_HEADER, unsafe_allow_html=True)

            # Knowledge base section
            st.markdown(
                '<div style="padding:20px 20px 8px;">'
                '<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#4B5563 !important;margin-bottom:10px;">Knowledge Base</p>'
                + "".join(
                    _company_row(info["label"], info["ticker"], info["fy"], f in upload_docs)
                    for f, info in COMPANY_INFO.items()
                )
                + "</div>",
                unsafe_allow_html=True,
            )

            # Divider
            st.markdown('<div style="height:1px;background:#1C2030;margin:0 20px;"></div>', unsafe_allow_html=True)

            # Upload section
            st.markdown(
                '<div style="padding:16px 20px 8px;">'
                '<p style="font-size:0.6rem;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#4B5563 !important;margin-bottom:10px;">Upload Filing</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            pdf_docs = st.file_uploader(
                "upload",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
            if pdf_docs:
                save_docs_to_vectordb(pdf_docs, upload_docs)

            # Extra uploaded files
            if len(upload_docs) > len(PRELOADED_FILINGS):
                extra = [f for f in upload_docs if f not in PRELOADED_FILINGS]
                for f in extra:
                    st.markdown(
                        f'<div style="padding:4px 20px;">'
                        f'<span style="font-size:0.75rem;color:#6B7280 !important;">📄 {f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Spacer + footer
            st.markdown(
                '<div style="position:fixed;bottom:0;width:258px;padding:16px 20px;'
                'background:#0C0F17;border-top:1px solid #1C2030;">'
                '<a href="https://github.com/vinay23is/financial-docs-rag" '
                'style="font-size:0.72rem;color:#4B5563 !important;text-decoration:none;">'
                '↗ View source on GitHub</a>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Main content ─────────────────────────────────────────────────────────
    def run(self):
        upload_docs = os.listdir("docs")
        self._render_sidebar(upload_docs)

        # Wrapper
        st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

        # Page header
        st.markdown(
            '<div class="page-header">'
            '<div class="eyebrow">Financial Intelligence</div>'
            '<h1>Ask the filings.</h1>'
            '<p class="sub">Query Apple, Alphabet, and Tesla\'s SEC 10-K annual reports in plain English. '
            'Answers are grounded in the actual filings — no hallucination.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Company chips
        chips_html = '<div class="chips-row">'
        for info in COMPANY_INFO.values():
            cls = info["chip"]
            chips_html += (
                f'<span class="chip {cls}">'
                f'<span class="dot"></span>'
                f'{info["ticker"]} · {info["fy"]}'
                f'</span>'
            )
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)

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
                self._render_empty_state()
        else:
            self._render_empty_state()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Empty state ───────────────────────────────────────────────────────────
    def _render_empty_state(self):
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="welcome-area">'
            '<p class="welcome-title">Where would you like to start?</p>'
            '<p class="welcome-sub">Select a question below or type your own.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # 2-column question card grid
        rows = [SAMPLE_QUESTIONS[i:i+2] for i in range(0, len(SAMPLE_QUESTIONS), 2)]
        for pair in rows:
            cols = st.columns(2)
            for col, (icon, q) in zip(cols, pair):
                with col:
                    st.markdown(
                        f'<div class="q-card">'
                        f'<span class="q-icon">{icon}</span>'
                        f'<span class="q-text">{q}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


if __name__ == "__main__":
    app = SECFilingAnalyzer()
    app.run()
