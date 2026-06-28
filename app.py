import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

import streamlit as st
from gtts import gTTS
import groq as groq_client

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_groq import ChatGroq
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DOC = BASE_DIR / "knowledge" / "mastermain.docx"

load_dotenv(BASE_DIR / ".env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="NEET Academy Assistant", page_icon="🎓")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing. Copy `.env.example` to `.env` and add your key.")
    st.stop()


@st.cache_resource
def load_vectorstore():
    if not KNOWLEDGE_DOC.exists():
        st.error(f"Knowledge file not found: {KNOWLEDGE_DOC}")
        st.stop()

    loader = Docx2txtLoader(str(KNOWLEDGE_DOC))
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.from_documents(splits, embeddings)


vectorstore = load_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})


def load_chain(retriever_obj):
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=GROQ_API_KEY,
        temperature=0,
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is.",
        ),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    contextualize_q_chain = contextualize_q_prompt | llm | StrOutputParser()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def retrieval_query(inputs):
        if inputs.get("chat_history"):
            return contextualize_q_chain.invoke(inputs)
        return inputs["input"]

    def retrieve_context(inputs):
        docs = retriever_obj.invoke(retrieval_query(inputs))
        return format_docs(docs)

    qa_system_prompt = (
        "You are a helpful and intelligent academy assistant.\n\n"
        "Answer the user's question using the provided context and the conversation history.\n\n"
        "Rules:\n\n"
        "* Always consider the previous conversation before answering the current question.\n"
        "* If the current question refers to something mentioned earlier using words such as \"they\", \"them\", \"some\", \"those\", \"it\", \"that\", \"these\", \"more\", \"which one\", or similar references, infer the subject from the previous conversation.\n"
        "* Treat follow-up questions as a continuation of the ongoing discussion.\n"
        "* Provide specific information from the context whenever available.\n"
        "* Do not respond with generic statements if relevant information exists in the context.\n"
        "* Rewrite information into natural, professional, and human-like language.\n"
        "* Do not copy raw text from the documents.\n"
        "* Preserve names, dates, numbers, course names, college names, and other factual information exactly as provided.\n"
        "* Do not invent information.\n"
        "* If the user asks for examples, names, lists, colleges, courses, achievements, statistics, or institute performance, share every relevant detail found in the context in a clear, positive summary.\n"
        "* When asked about performance, results, success, or achievements, present all available facts (numbers, rankings, placements, pass rates, student counts, awards, etc.) as the answer. Do not list what is missing or comment on gaps in the document.\n"
        "* Never say phrases like \"the document does not provide\", \"no information on\", \"it is not possible to provide\", or similar meta-commentary about the knowledge base or source material.\n"
        "* Never describe what the document focuses on instead of answering the question.\n"
        "* If only partial performance information exists, answer with what is available and stop. Do not apologize for incomplete data or explain limitations.\n"
        "* Only respond with \"I could not find this information in the knowledge base.\" if neither the conversation history nor the retrieved context contains any relevant information at all.\n"
        "* Answer naturally as if you are continuing a real conversation with the user.\n\n"
        "Context:\n"
        "{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    return (
        RunnablePassthrough.assign(context=retrieve_context)
        | qa_prompt
        | llm
        | StrOutputParser()
    )


qa_chain = load_chain(retriever)


def speech_to_text(audio_bytes):
    try:
        client = groq_client.Groq(api_key=GROQ_API_KEY)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name

        with open(temp_audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3",
                response_format="text",
            )
        os.unlink(temp_audio_path)
        return transcription.strip()
    except Exception as e:
        return f"Voice Error: {e}"


def text_to_speech(text):
    tts = gTTS(text=text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_path = temp_file.name
    tts.save(temp_path)
    return temp_path


st.title("🎓 NEET Academy Assistant")
st.markdown("Ask questions from the academy knowledge base using text or voice.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.last_processed_audio = None
    st.rerun()

st.markdown("### Suggestions")
cols = st.columns(3)
suggestion = None
if cols[0].button("Academy Timings"):
    suggestion = "What are the academy timings?"
if cols[1].button("Courses Available"):
    suggestion = "What courses are available?"
if cols[2].button("Fee Structure"):
    suggestion = "What is the fee structure?"

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio" in msg and msg["audio"]:
            st.audio(msg["audio"], format="audio/mp3")

user_input = st.chat_input("Ask your question...")
audio_input = st.audio_input("🎤 Voice Input")

prompt_text = None

if suggestion:
    prompt_text = suggestion
elif user_input:
    prompt_text = user_input
elif audio_input is not None:
    if hasattr(audio_input, "file_id"):
        current_audio_id = audio_input.file_id
    else:
        current_audio_id = hash(audio_input.getvalue())

    if st.session_state.last_processed_audio != current_audio_id:
        with st.spinner("Transcribing audio..."):
            audio_bytes = audio_input.getvalue()
            prompt_text = speech_to_text(audio_bytes)
        st.session_state.last_processed_audio = current_audio_id
        if prompt_text.startswith("Voice Error:"):
            st.error(prompt_text)
            prompt_text = None

if prompt_text:
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    with st.chat_message("user"):
        st.markdown(prompt_text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history_msgs = st.session_state.messages[:-1]
            chat_history = []
            for m in history_msgs:
                if m["role"] == "user":
                    chat_history.append(HumanMessage(content=m["content"]))
                else:
                    chat_history.append(AIMessage(content=m["content"]))

            response = qa_chain.invoke({
                "input": prompt_text,
                "chat_history": chat_history,
            })
            st.markdown(response)

            audio_path = text_to_speech(response)
            st.audio(audio_path, format="audio/mp3", autoplay=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "audio": audio_path,
            })
