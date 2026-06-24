import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

# ================= CONFIG =================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in environment variables")

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================

conn = sqlite3.connect("memory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
)
""")
conn.commit()

# ================= SYSTEM PROMPT =================

SYSTEM_PROMPT = """
You are Memory AI Pro — built by Deepu.
You are a highly professional, intelligent AI assistant.

IMPORTANT RULES:
1. Always reply in Hinglish (Hindi + English mix) unless user specifically asks in pure English or pure Hindi.
2. Be professional like ChatGPT — give structured, detailed answers.
3. Use headings, bullet points, numbered lists when needed.
4. Think step-by-step before answering complex questions.
5. ALWAYS remember past conversations. If user told their name, work, hobby, food preference — use it naturally in future replies.
6. Be friendly but professional. Use "bhai", "yaar" occasionally to feel natural.
7. If user asks in Hindi, reply in Hindi. If English, reply in English. Default is Hinglish.
8. Never give short lazy answers. Always explain properly.
9. If you don't know something, say honestly.
10. You have long-term memory — use previous chat context smartly.
"""

# ================= MODEL =================

class ChatRequest(BaseModel):
    user_id: str = "default"
    message: str

# ================= ROUTES =================

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("manifest.json")

@app.get("/service-worker.js")
async def sw():
    return FileResponse("service-worker.js")

@app.get("/icon-152.png")
async def icon152():
    return FileResponse("icon-152.png")

@app.get("/icon-192.png")
async def icon192():
    return FileResponse("icon-192.png")

@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        user_id = req.user_id
        message = req.message

        if not message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        cursor.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, "user", message, datetime.utcnow().isoformat())
        )
        conn.commit()

        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
        """, (user_id,))
        rows = cursor.fetchall()
        rows.reverse()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend([{"role": r[0], "content": r[1]} for r in rows])
        messages.append({"role": "user", "content": message})

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            stream=True
        )

        async def stream():
            full_response = ""
            for chunk in completion:
                content = chunk.choices[0].delta.content or ""
                full_response += content
                yield content

            cursor.execute(
                "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "assistant", full_response, datetime.utcnow().isoformat())
            )
            conn.commit()

        return StreamingResponse(stream(), media_type="text/plain")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
