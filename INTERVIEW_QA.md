# Interview Q&A — SEC Filing Analyzer (RAG Chatbot)

Use this as a study guide before interviews. These answers are calibrated for a software engineering / ML engineering interview, not a research role.

---

## 1. What is RAG and why did you use it?

**RAG (Retrieval-Augmented Generation)** is a pattern where you retrieve relevant documents at query time and inject them into the LLM's prompt, rather than relying on the model's baked-in training knowledge.

**Why I used it:**
- SEC 10-K filings are updated annually. I'd need to retrain or fine-tune a model to update its knowledge — with RAG I just update the document store.
- RAG answers are **verifiable** — I show users which source pages were used, so they can fact-check the response.
- **No hallucination on specific numbers**: The model is instructed to only answer from retrieved context; if the figure isn't there, it says so rather than inventing it.
- Far cheaper than fine-tuning. No GPU training costs.

**The tradeoff:** RAG can fail if the retrieval step returns the wrong chunks. The answer is only as good as what gets retrieved. Fine-tuning would bake the knowledge in more deeply, but it's static and expensive.

---

## 2. Why ChromaDB?

ChromaDB is an **open-source, embedded vector database** that runs in-process and persists to disk.

**Why it fits this project:**
- **Zero infrastructure** — no separate database server to spin up, no cloud account needed. The vector store is just a folder on disk.
- **Free** — no API keys, no usage limits, no monthly bill.
- **LangChain native** — LangChain has first-class ChromaDB support, so integration is a few lines.
- **Persistence** — ChromaDB writes to disk, so vectors survive app restarts. Users don't re-embed on every session.

**When I'd switch:** At production scale (millions of documents, multiple users, low-latency SLAs), I'd move to **Pinecone** (managed, fast, scales horizontally) or **Weaviate** (self-hosted, supports hybrid search). ChromaDB doesn't handle concurrent writes well and isn't designed for distributed workloads.

---

## 3. Why Gemini over OpenAI?

| Factor | Gemini 1.5-flash | OpenAI GPT-4o-mini |
|--------|-----------------|-------------------|
| Cost | Free tier (15 RPM, 1M TPM) | $0.15/1M input tokens |
| Context window | 1,000,000 tokens | 128,000 tokens |
| Embeddings | `embedding-001` (same ecosystem) | Separate `text-embedding-3-small` |
| Latency | Fast | Fast |

For a portfolio project that others should be able to clone and run, **zero cost is a hard requirement**. Gemini's free tier is generous enough for demo and development. The 1M-token context window also means I could theoretically feed an entire 10-K in one shot if needed, though RAG is still preferable for speed and precision.

**I'd switch to OpenAI** if I needed function calling capabilities, fine-tuning support, or if a client's infrastructure was already OpenAI-based.

---

## 4. How does the chunking work?

I use LangChain's `RecursiveCharacterTextSplitter` with:
- **chunk_size = 2,000 characters** (~500 tokens)
- **chunk_overlap = 200 characters**
- **Separators**: `["\n\n", "\n", ". ", " ", ""]` — tries to break at paragraph boundaries first, then sentence boundaries, then words

**Why these values:**
- 2,000 chars keeps each chunk focused on one topic (e.g., one risk factor, one revenue discussion) without being too narrow to lose context.
- 200-char overlap ensures a sentence that straddles a boundary doesn't get split in a way that loses meaning. Both neighboring chunks will contain it.
- The separator hierarchy means we prefer to break at natural paragraph/sentence boundaries rather than mid-word.

**The tradeoff:** Larger chunks = more context per retrieval, but the embedding must represent more content, potentially diluting similarity scores for specific queries. Smaller chunks = more precise retrieval, but the answer might lack surrounding context. 2,000 chars is a reasonable middle ground for financial prose.

---

## 5. What happens when a user asks a question?

Step-by-step flow:

1. **User types a question** in the Streamlit chat input.
2. **Embedding** — The question text is sent to Google's `embedding-001` model, which returns a 768-dimensional vector representation.
3. **Similarity search** — ChromaDB compares this query vector against all stored chunk vectors using **cosine similarity**. The top 5 most similar chunks are retrieved.
4. **Prompt construction** — LangChain's `create_retrieval_chain` builds a prompt that includes:
   - System prompt (financial analyst persona, instruction to only use context)
   - Retrieved chunks (injected as `{context}`)
   - Chat history (last N exchanges as `HumanMessage`/`AIMessage` objects)
   - The user's question
5. **LLM call** — This prompt is sent to Gemini 1.5-flash, which generates a grounded answer.
6. **Response display** — The answer is shown in the chat. Source file names and page numbers are displayed in the sidebar.
7. **History update** — The question and answer are appended to `chat_history` in Streamlit's session state, so follow-up questions have context.

---

## 6. What would you improve with more time?

**Retrieval quality:**
- **Hybrid search**: Combine vector search with BM25 keyword search. Pure semantic search can miss exact matches for specific dollar figures ("$383.3 billion"). BM25 catches those exact tokens; a weighted rerank of both would improve precision.
- **Reranking**: After retrieving top-10 chunks, run a cross-encoder reranker to reorder them by relevance before passing to the LLM.

**Document processing:**
- **Table extraction**: `PyPDF` doesn't handle financial tables well — numbers from multi-column tables often get concatenated incorrectly. `pdfplumber` or `Camelot` would extract tabular data more accurately.
- **Multi-year filings**: Load 3-5 years of 10-Ks per company to enable trend analysis queries ("How has Apple's gross margin changed over 5 years?").

**Production readiness:**
- **Streaming**: Stream Gemini tokens to the UI so users see the response being typed rather than waiting for the full answer.
- **Caching**: Cache embedding calls for repeated queries using `st.cache_data`.
- **Evaluation**: Build a RAGAS test suite measuring answer faithfulness, context recall, and answer relevance on a golden QA dataset.
- **Auth**: Add user authentication before exposing to the public.

---

## 7. How is the conversation history handled?

Streamlit session state stores `chat_history` as a list of LangChain `HumanMessage` and `AIMessage` objects. On each chat turn:
1. The full history is passed to the retrieval chain via `MessagesPlaceholder`.
2. The new question + answer is appended to the list.
3. Streamlit re-renders the full chat history on each rerun.

**Why LangChain message objects instead of plain strings?**
LangChain's `ChatPromptTemplate` with `MessagesPlaceholder` automatically formats these into the correct role structure (`user`/`assistant`) expected by the Gemini chat API. Using plain strings would require manual formatting.

**Limitation:** History grows unboundedly. In production I'd cap it at the last N turns or use a summarization approach (compress old history into a running summary) to stay within the context window budget.

---

## 8. How is the app deployed and what are its infrastructure costs?

- **Hosting**: Streamlit Community Cloud (free, supports public GitHub repos)
- **Database**: ChromaDB on Streamlit's ephemeral filesystem — the vector store rebuilds on each cold start (acceptable for a demo; a persistent file store or external DB would fix this in production)
- **LLM/Embeddings**: Google AI Studio free tier
- **Total monthly cost: $0**

For a production version serving real users, I'd move to:
- Pinecone Serverless (vector store — persistent, scalable)
- Render or Railway (app hosting — persistent disk, ~$7/month)
- Gemini API paid tier or OpenAI for SLA guarantees
