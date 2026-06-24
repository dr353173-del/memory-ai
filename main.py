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
You are Memory AI Pro — a professional AI assistant like ChatGPT.

- Respond clearly and professionally
- Use structured answers
- Think step-by-step
- Use previous chat context
- Avoid unnecessary emojis
"""

# ================= MODEL =================

class ChatRequest(BaseModel):
    user_id: str = "default"
    message: str

# ================= ROUTES =================

@app.get("/")
async def home():
    return FileResponse("index.html")

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

        # Save user message
        cursor.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, "user", message, datetime.utcnow().isoformat())
        )
        conn.commit()

        # Load history
        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 15
        """, (user_id,))
        rows = cursor.fetchall()
        rows.reverse()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend([{"role": r[0], "content": r[1]} for r in rows])
        messages.append({"role": "user", "content": message})

        # Call Groq with streaming
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
