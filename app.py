import os
os.environ["STREAMLIT_SERVER_ENABLE_FILE_WATCHER"] = "false"
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

try:
    import torch
    torch.classes.__path__ = []
except ImportError:
    pass

import tempfile
import hashlib
import streamlit as st
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.chains import RetrievalQA
from gtts import gTTS
import groq as groq_client

# ---------------- LOAD ENV ----------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------- STREAMLIT CONFIG ----------------
st.set_page_config(
    page_title="NEET Academy Assistant",
    page_icon="🎓",
    layout="centered"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Typography & Font Family */
    html, body, [class*="css"], .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, button, input, label, textarea {
        font-family: 'Outfit', sans-serif !important;
    }

    /* App Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #1e1b4b 100%) !important;
        color: #f8fafc !important;
    }

    /* Premium Animated Gradient Title */
    .premium-title {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #ec4899, #6366f1);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        font-size: 2.8rem !important;
        margin-bottom: 0.2rem !important;
        animation: gradient-animation 8s ease infinite;
        text-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
    }
    
    @keyframes gradient-animation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Subtitle Styling */
    .subtitle {
        color: #94a3b8 !important;
        font-size: 1.1rem !important;
        margin-bottom: 2rem !important;
    }

    /* Glassmorphism Chat Bubble Styling */
    div[data-testid="stChatMessage"] {
        background-color: rgba(17, 24, 39, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
    }

    div[data-testid="stChatMessage"]:hover {
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.1), 0 10px 10px -5px rgba(99, 102, 241, 0.04);
        transform: translateY(-2px);
    }

    /* Assistant Message Glassmorphism Specific */
    div[data-testid="stChatMessage"][data-testid="stChatMessage-assistant"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
    }

    /* Sidebar Container styling */
    section[data-testid="stSidebar"] {
        background-color: #030712 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* Sidebar inner element enhancements */
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p {
        color: #94a3b8;
    }

    /* Custom Streamlit Audio Input Widget Wrapper */
    div.stAudioInput {
        background: rgba(17, 24, 39, 0.8) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
        padding: 0.5rem !important;
    }

    /* Chat input overrides */
    div[data-testid="stChatInput"] textarea {
        background-color: rgba(17, 24, 39, 0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
        font-size: 1rem !important;
    }

    div[data-testid="stChatInput"] textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    /* Audio block styling */
    audio {
        border-radius: 8px;
        margin-top: 0.5rem;
        width: 100%;
    }

    /* Buttons styling */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# Main Title and Subtitle with classes
st.markdown("<h1 class='premium-title'>🎓 NEET Academy Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Ask questions from the academy master document or record your voice question.</p>", unsafe_allow_html=True)

# ---------------- LOAD LLM ----------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
    temperature=0
)

# ---------------- LOAD DOCUMENT ----------------
@st.cache_resource
def load_vectorstore():
    loader = UnstructuredWordDocumentLoader(
        "knowledge/master.docx"
    )
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = FAISS.from_documents(
        splits,
        embeddings
    )
    return vectorstore

vectorstore = load_vectorstore()

# ---------------- PROMPT ----------------
prompt_template = """
You are a NEET academy assistant.

Answer ONLY from the provided context.

If the answer is not available in the context say:
"I can answer only from the academy knowledge base."

Context:
{context}

Question:
{question}

Answer:
"""

# ---------------- QA CHAIN ----------------
PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(
        search_kwargs={"k": 4}
    ),
    chain_type="stuff",
    chain_type_kwargs={
        "prompt": PROMPT
    }
)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "processed_audio_hash" not in st.session_state:
    st.session_state.processed_audio_hash = None

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### 🎓 Assistant Controls")
    st.markdown("Use this panel to clear conversation history or record your questions via microphone.")
    st.markdown("---")
    
    st.markdown("#### 🎙️ Voice Input")
    st.markdown("Click below to record your question:")
    audio_file = st.audio_input("Record voice question", label_visibility="collapsed")
    
    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.processed_audio_hash = None
        st.rerun()

    st.markdown("---")
    st.markdown("#### 💡 Sample Questions")
    st.markdown("- *What are the academy timings?*")
    st.markdown("- *How can I enroll in the NEET course?*")
    st.markdown("- *What is the refund policy?*")

# ---------------- DISPLAY CHAT ----------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------- VOICE TRANSCRIBE FUNCTION ----------------
def speech_to_text(audio_file):
    try:
        client = groq_client.Groq(api_key=GROQ_API_KEY)
        audio_bytes = audio_file.read()
        audio_file.seek(0)

        import io
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3",
            response_format="text"
        )
        return transcription.strip()
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return None

# ---------------- TEXT TO SPEECH ----------------
def text_to_speech(text):
    tts = gTTS(text=text)
    temp_audio = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )
    tts.save(temp_audio.name)
    return temp_audio.name

# ---------------- PROCESS INPUTS ----------------
user_question = st.chat_input("Ask your question...")

# Process voice input from sidebar if present
if audio_file is not None:
    audio_bytes = audio_file.read()
    audio_file.seek(0)
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    
    # Process only if this is a new recording
    if audio_hash != st.session_state.processed_audio_hash:
        st.session_state.processed_audio_hash = audio_hash
        with st.spinner("Transcribing voice question..."):
            voice_text = speech_to_text(audio_file)
            if voice_text and len(voice_text.strip()) > 0:
                user_question = voice_text
                st.sidebar.success(f"🎤 Heard: {voice_text}")
            else:
                st.sidebar.warning("Could not understand the audio. Please try again.")
elif st.session_state.processed_audio_hash is not None:
    # Reset hash tracker if audio input is cleared
    st.session_state.processed_audio_hash = None

# ---------------- PROCESS & RESPOND ----------------
if user_question:
    # Add user message to history
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question
        }
    )
    
    # Render user message
    with st.chat_message("user"):
        st.markdown(user_question)
        
    # Render and run assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = qa_chain.run(user_question)
            st.markdown(response)
            
            # Generate and play TTS audio
            try:
                audio_path = text_to_speech(response)
                st.audio(audio_path)
            except Exception as tts_err:
                st.warning(f"Voice playback unavailable: {tts_err}")
                
    # Add assistant response to history
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )
