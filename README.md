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

## Deploy on Streamlit Cloud

1. Push this repo to GitHub (do **not** commit `.env` or `myenv/`).
2. Create a new app at [share.streamlit.io](https://share.streamlit.io) pointing to `app.py`.
3. Under **Secrets**, add:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   ```
4. Ensure `knowledge/mastermain.docx` is included in the repo.

## Project layout

```
Voiceagent_final/
├── app.py              # Streamlit application
├── requirements.txt    # Python dependencies
├── knowledge/          # Academy knowledge base (.docx)
├── .env                # API keys (create from .env.example)
└── .streamlit/         # Streamlit config
```
