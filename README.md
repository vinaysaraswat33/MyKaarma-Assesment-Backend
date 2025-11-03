# 📱 MyKaarma Assessment – Backend (FastAPI + Groq)

This is the backend service for the **MyKaarma Assessment Project**, which powers an AI-driven smartphone recommendation and comparison assistant.
It uses **FastAPI** for the API layer and **Groq LLM (LLaMA 3.3)** for intelligent language understanding.

## 🚀 Tech Stack

* **Framework:** FastAPI
* **Language Model:** Groq (LLaMA-3.3-70B)
* **Environment Management:** python-dotenv
* **Hosting:**  Vercel
* **Dataset:** Static JSON (`data/phones.json`)
* **CORS Enabled:** Frontend (Vercel) + Localhost

---

## 📂 Project Structure

```
backend/
│
├── data/
│   └── phones.json              # Static dataset of smartphone specs
│
├── app.py                        # FastAPI app entry point
├── model.py                      # Implementing llm calls
├── service.py                    # Chat service implementation 
├── utils.py                      # Utility functions
├── schema.py                     # Model schema                    
│
├── .env                         # Environment variables (Groq API Key)
│
├── requirements.txt             # Python dependencies
│
└── README.md                    # Documentation
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-username>/MyKaarma-Assesment-Backend.git
cd MyKaarma-Assesment-Backend
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate     # (Mac/Linux)
venv\Scripts\activate        # (Windows)
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Create `.env` File

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 5️⃣ Run Server Locally

```bash
uvicorn main:app --reload
```

### 6️⃣ Access Endpoints

* **Base URL:** `http://localhost:8000`
* **Health Check:** `/healthz`
* **Chat Endpoint:** `/chat`

---



## 🧠 Key Features

✅ Intent classification (`search`, `compare`, `details`, `explain`)
✅ Context-aware conversations
✅ Groq-based intelligent reasoning
✅ Real smartphone dataset with scoring
✅ Optimized retrieval ranking and summarization



## 🧩 Backend Architecture

```
                    ┌────────────────────┐
                    │  React Frontend    │
                    └───────┬────────────┘
                            │
                            ▼
                ┌────────────────────────────┐
                │      FastAPI Backend        │
                │────────────────────────────│
                │  • /chat endpoint           │
                │  • Intent Parsing           │
                │  • Context Handling         │
                │  • Phone Retrieval          │
                │  • Groq API Integration     │
                └─────────────┬──────────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │   Groq LLM (LLaMA 3.3)     │
                └────────────────────────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │    phones.json Dataset      │
                └────────────────────────────┘
```

---

## 🧾 License

This project is for assessment and demonstration purposes only.
