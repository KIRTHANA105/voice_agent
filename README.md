# NEET Academy Assistant

Voice-enabled RAG chatbot for academy questions, powered by Groq and Streamlit.

## Setup

```powershell
cd Voiceagent_final
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set your GROQ_API_KEY
```

## Run

```powershell
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project layout

```
Voiceagent_final/
├── app.py              # Streamlit application
├── requirements.txt    # Python dependencies
├── knowledge/          # Academy knowledge base (.docx)
├── .env                # API keys (create from .env.example)
└── .streamlit/         # Streamlit config
```
