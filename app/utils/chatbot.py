import os
import streamlit as st
from collections import defaultdict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

SYSTEM_PROMPT = """You are an expert financial analyst specializing in SEC annual filings (10-K reports).
You have access to 10-K filing summaries for Apple (AAPL), Alphabet/Google (GOOGL), and Tesla (TSLA),
as well as any additional documents the user has uploaded.

Your job is to answer questions accurately using the retrieved content from these filings.
- Cite specific figures (revenue, net income, EPS, etc.) when available.
- If a question cannot be answered from the provided context, say so clearly — do not invent numbers.
- When comparing companies, be precise about which fiscal year each figure refers to.
- If the user asks about a company not in the loaded documents, let them know they can upload additional filings.

Answer the question using this context from the SEC filings:
{context}"""

def _get_api_key():
    load_dotenv()
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return os.getenv("GOOGLE_API_KEY")

def get_response(question, chat_history, vectordb):
    api_key = _get_api_key()

    # Retrieve relevant chunks manually (avoids langchain.chains dependency)
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(question)
    context = "\n\n".join(doc.page_content for doc in docs)

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.1,
        google_api_key=api_key,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "context": context,
        "chat_history": chat_history,
        "input": question,
    })
    return answer, docs

def chat(chat_history, vectordb):
    user_query = st.chat_input("Ask about any company's financials...")
    if user_query:
        with st.spinner("Analyzing filings..."):
            response, docs = get_response(user_query, chat_history, vectordb)
        chat_history = chat_history + [
            HumanMessage(content=user_query),
            AIMessage(content=response),
        ]
        with st.sidebar:
            if docs:
                st.markdown("---")
                st.markdown("**Sources used:**")
                metadata_dict = defaultdict(list)
                for doc in docs:
                    src = os.path.basename(doc.metadata.get("source", "Unknown"))
                    metadata_dict[src].append(doc.metadata.get("page", 0))
                for src, pages in metadata_dict.items():
                    page_str = ", ".join(str(p + 1) for p in sorted(set(pages)))
                    st.markdown(f"📄 **{src}** — p. {page_str}")

    for message in chat_history:
        role = "assistant" if isinstance(message, AIMessage) else "user"
        with st.chat_message(role):
            st.write(message.content)

    return chat_history
