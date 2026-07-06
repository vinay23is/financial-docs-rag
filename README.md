# SEC Filing Analyzer — RAG-Powered Financial Document Chatbot

Chat with SEC 10-K annual reports in plain English and get answers grounded in the actual filing text, with source pages cited so you can verify every claim.

**Live Demo:** [financial-docs-rag.streamlit.app](https://financial-docs-rag-bky4wws43jxf6xxvty4yhn.streamlit.app/)

> **Note on origin:** this repo started as a fork of [vitorccmanso/Rag-ChatBot](https://github.com/vitorccmanso/Rag-ChatBot), a generic document-chat template (app skeleton, chunking/embedding utilities, Streamlit chat loop). Everything on top of that base is original work: repurposing it into a domain-specific SEC-filing analyzer, swapping the LLM/embedding stack, a full UI redesign, an AWS Lambda + FAISS backend, an offline evaluation harness, and CI. The diff against the fork point is roughly 2,000 added lines across 21 files — see `git log` for the full commit history from `f9d7d0d` onward.

## What problem does this solve?
SEC 10-K filings are the best source for understanding a public company's financial health, risks, and strategy, but they're dense, jargon-heavy, and often 100+ pages long. Analysts spend hours hunting for a specific number or comparing disclosures across companies. This project lets you ask questions like "What were Apple's biggest risk factors this year?" or "Compare Tesla's and Alphabet's R&D spending" and get an answer backed by the actual filing text, with the source page shown so you can check it yourself.

## Tech Stack
- **Frontend:** Streamlit (chat UI, source-citation sidebar, file upload for custom filings)
- **LLM:** Google Gemini (`gemini-flash-latest`) via `langchain-google-genai`
- **Embeddings:** Google `gemini-embedding-001`
- **RAG framework:** LangChain (LCEL — pure `langchain_core` chains, no `langchain.chains` dependency)
- **Vector store:** ChromaDB locally (Streamlit deployment); FAISS in the AWS Lambda backend
- **Backend (optional remote mode):** AWS Lambda handler (`lambda/handler.py`) serving the same RAG pipeline over an API, with the FAISS index snapshot pulled from S3
- **PDF parsing:** PyPDF
- **CI/Eval:** GitHub Actions workflow running a smoke-test evaluation script on push

## Architecture
```
User Question
     |
     v
 Embedding Model (Gemini gemini-embedding-001)
     |
     v
 Vector Store (ChromaDB local / FAISS in Lambda)  <-- SEC 10-K PDFs (pre-indexed)
     |  (similarity search, top-5 chunks)
     v
 Gemini gemini-flash-latest (LLM)  <-- chat history + domain system prompt
     |
     v
 Grounded answer + cited source pages
```
The app can run in two modes, chosen automatically by `chatbot.py`: **local mode** embeds and retrieves directly against a local ChromaDB store, and **remote mode** (when `RAG_API_URL` is set) forwards the question and chat history to the AWS Lambda endpoint instead, which runs the same retrieval + generation pipeline against a FAISS index stored in S3. This lets the same Streamlit frontend run standalone or against a decoupled backend.

## Key Features
- Chat interface answers questions about pre-loaded 10-K filings for Apple, Alphabet, and Tesla, and lets users upload their own SEC PDFs to extend the knowledge base.
- Every answer shows which filing and page numbers it was generated from, so answers are verifiable rather than taken on faith.
- Offline evaluation harness (`evaluate.py`) runs 25 fixed queries against the pipeline and scores retrieval precision, "groundedness" (whether every multi-digit number in the answer actually appears in retrieved context), and latency.
- GitHub Actions CI (`ci_eval.py` + `.github/workflows/eval.yml`) runs a smoke-test evaluation on every push.
- Dual deployment paths: a self-contained Streamlit Cloud app, and an AWS Lambda + API Gateway backend (`deploy.sh`, `lambda/handler.py`) for a decoupled architecture.

![App in use](Images/app_in_use.png)
![Project schema](Images/project_schema.png)
![User interface](Images/user_interface.png)

## Interesting Engineering Decisions
- **Groundedness as a measurable metric, not a hope:** `evaluate.py` flags an answer as ungrounded if it contains a 4+ digit number that doesn't appear anywhere in the retrieved context — a cheap, concrete proxy for catching hallucinated figures in a financial-data chatbot, where a wrong number is worse than no answer.
- **Local/remote mode switch lives in one function:** `chatbot.get_response()` checks for a `RAG_API_URL` env var and transparently routes to either the local ChromaDB retriever or the Lambda API, using a `_FakeDoc` shim so the calling code doesn't need to know which mode it's in. That kept the Streamlit UI code unchanged when the Lambda backend was added later.
- **FAISS in Lambda, ChromaDB in Streamlit:** the two deployment targets use different vector stores on purpose — ChromaDB needs a writable local disk and persistent process, which doesn't fit Lambda's stateless, read-only-filesystem execution model, so the Lambda path loads a pre-built FAISS index snapshot from S3 on cold start instead.
- **Gemini over OpenAI:** chosen for the free tier (generous RPM/TPM limits), a 1M-token context window, and because the embedding model (`gemini-embedding-001`) is in the same ecosystem as the LLM — no second API key or billing account needed to run the project.

## Running Locally
```bash
git clone https://github.com/vinay23is/financial-docs-rag.git
cd financial-docs-rag
python -m venv venv
source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt

cp .env.example .env
# add your GOOGLE_API_KEY to .env

streamlit run app/app.py
```
The app opens at `http://localhost:8501` with three pre-loaded SEC filing PDFs (AAPL, GOOGL, TSLA) — start chatting immediately, or upload your own filing from the sidebar.

Run the offline evaluation suite:
```bash
python evaluate.py
```

Deploy your own copy on Streamlit Community Cloud: push to your GitHub, create a new app pointing at `app/app.py`, and add `GOOGLE_API_KEY` under Secrets.

---
*Data sourced from SEC EDGAR public filings. Not investment advice.*
