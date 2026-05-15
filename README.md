# 📊 SEC Filing Analyzer — RAG-Powered Financial Document Chatbot

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.2%2B-1C3C3C?style=flat&logo=chainlink&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-FF6B35?style=flat)
![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0--flash-4285F4?style=flat&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **Ask plain-English questions about SEC 10-K annual reports and get AI-generated answers backed by real filing data.**

**Live Demo:** [Coming soon — deploy link here]

---

## The Problem This Solves

SEC 10-K annual reports are the gold standard for understanding a public company's financial health, risks, and strategy — but they're dense, jargon-heavy, and often 100+ pages long. Analysts and investors spend hours hunting for specific figures or comparing disclosures across companies.

This project lets you **chat with those filings naturally**:
- *"What were Apple's biggest risk factors this year?"*
- *"Compare Tesla's and Alphabet's R&D spending."*
- *"What did Google's MD&A say about Cloud growth?"*

---

## How It Works (RAG Architecture)

```
User Question
     │
     ▼
 Embedding Model (Google text-embedding-001)
     │
     ▼
 ChromaDB Vector Store ◄── SEC 10-K PDFs (pre-indexed)
     │  (cosine similarity search)
     ▼
 Top-K Relevant Chunks
     │
     ▼
 Gemini 1.5-flash (LLM)  ◄── Chat History + System Prompt
     │
     ▼
 Grounded Answer
```

1. **Ingestion** — SEC filing PDFs are split into overlapping chunks (2,000 chars / 200 overlap) and embedded using Google's `embedding-001` model.
2. **Storage** — Vectors are persisted in a local ChromaDB store (no external database needed).
3. **Retrieval** — On each user query, the question is embedded and the top-5 most semantically similar chunks are retrieved.
4. **Generation** — The retrieved chunks + conversation history are passed to Gemini 1.5-flash with a domain-specific system prompt, producing a grounded answer.
5. **Source display** — The sidebar shows which filing pages were used to generate each answer, enabling verification.

---

## Pre-loaded Companies

| Company | Ticker | Filing | Source |
|---------|--------|--------|--------|
| Apple Inc. | AAPL | FY2025 10-K Summary | SEC EDGAR |
| Alphabet Inc. | GOOGL | FY2024 10-K Summary | SEC EDGAR |
| Tesla, Inc. | TSLA | FY2025 10-K Summary | SEC EDGAR |

You can also upload your own SEC PDF filings via the sidebar to expand the knowledge base.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Google Gemini 2.0-flash | Free tier, fast, multimodal, 1M context window |
| Embeddings | Google `embedding-001` | Paired with Gemini; no extra cost |
| Vector DB | ChromaDB | Open-source, persists to disk, no server needed |
| RAG Framework | LangChain | Composable chains, well-documented, industry standard |
| UI | Streamlit | Rapid prototyping, easy cloud deployment |
| PDF Parsing | PyPDF | Lightweight, handles multi-page documents |

---

## Run Locally

### Prerequisites
- Python 3.10+
- A free [Google AI Studio API key](https://aistudio.google.com/app/apikey) (Gemini)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/vinay23is/financial-docs-rag.git
cd financial-docs-rag

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env
# Open .env and replace "your-gemini-api-key-here" with your actual key

# 5. Run the app
streamlit run app/app.py
```

The app opens at `http://localhost:8501`. The three SEC filing PDFs are pre-loaded — start chatting immediately.

---

## Deploy on Streamlit Cloud (Free)

1. Push this repo to your GitHub account.
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud) and sign in with GitHub.
3. Click **"New app"** → select this repo → set main file to `app/app.py`.
4. Under **"Advanced settings"** → **Secrets**, add:
   ```toml
   GOOGLE_API_KEY = "your-gemini-api-key-here"
   ```
5. Click **Deploy**. Done — free hosting, no server management.

---

## Project Structure

```
financial-docs-rag/
├── app/
│   ├── app.py                  # Main Streamlit UI
│   ├── sec_filings/            # Pre-built SEC 10-K summary PDFs
│   │   ├── AAPL_10K_Summary.pdf
│   │   ├── GOOGL_10K_Summary.pdf
│   │   └── TSLA_10K_Summary.pdf
│   └── utils/
│       ├── chatbot.py          # LangChain RAG chain, Gemini integration
│       ├── prepare_vectordb.py # PDF loading, chunking, ChromaDB creation
│       ├── save_docs.py        # Handles user file uploads
│       └── session_state.py    # Streamlit session management, pre-loads SEC filings
├── .streamlit/
│   └── config.toml             # Theme and server config
├── .env.example                # API key template
├── requirements.txt
└── README.md
```

---

## Key Design Decisions

**Why RAG instead of fine-tuning?**
Fine-tuning bakes knowledge into the model weights — it's expensive, requires retraining when filings are updated, and the model can still hallucinate. RAG keeps the source documents as the ground truth and retrieves them at query time, making answers verifiable and the knowledge base easily updateable.

**Why ChromaDB over Pinecone/Weaviate?**
ChromaDB runs entirely locally and persists to disk — zero infrastructure cost, zero latency to an external service, and no API keys to manage. For a portfolio project and small-to-medium document sets, it's the right tradeoff. Pinecone or Weaviate would be appropriate at production scale.

**Why Gemini 1.5-flash over OpenAI GPT?**
Gemini 1.5-flash is free on Google AI Studio's tier (15 RPM, 1M TPM), has a massive 1M-token context window, and the `embedding-001` model pairs naturally with it. OpenAI's equivalent usage costs money and adds a paid dependency that makes this project inaccessible to others.

**Why chunk at 2,000 characters with 200 overlap?**
SEC filings use dense financial prose with cross-references. Larger chunks preserve more context per retrieval; 200-character overlap ensures sentences that span chunk boundaries don't lose meaning. The overlap trades storage for answer quality.

---

## Screenshot

> *(Add screenshot after deploying)*

![App Screenshot](Images/screenshot_placeholder.png)

---

## What I'd Improve with More Time

- **Streaming responses** — stream Gemini tokens to the UI for a more responsive feel
- **Hybrid search** — combine vector similarity with BM25 keyword search (better recall on specific figure lookups like exact dollar amounts)
- **Multi-year comparisons** — load multiple years of 10-Ks per company for trend analysis
- **Table extraction** — use a specialized PDF parser (Camelot/pdfplumber) to better extract financial tables, which PyPDF sometimes mangles
- **Evaluation** — build a RAGAS evaluation suite to measure answer faithfulness and context recall

---

## About

Built by **Vinay Dodla** as a portfolio project demonstrating practical RAG system design with real-world financial data.

- [GitHub](https://github.com/vinay23is)
- [LinkedIn](https://linkedin.com/in/vinaydodla)

---

*Data sourced from SEC EDGAR public filings. Not investment advice.*
