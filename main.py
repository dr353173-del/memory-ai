import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

# ================= CONFIG =================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set")

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ IMPORTANT — Serve static folder as root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

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

# ================= HELPERS =================

def save_message(user_id, role, content):
    cursor.execute(
        "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (user_id, role, content, datetime.utcnow().isoformat())
    )
    conn.commit()

def get_recent_messages(user_id, limit=15):
    cursor.execute("""
        SELECT role, content FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]

# ================= CHAT API =================

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id", "default")
        message = data.get("message")

        if not message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        save_message(user_id, "user", message)
        history = get_recent_messages(user_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
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
            save_message(user_id, "assistant", full_response)

        return StreamingResponse(stream(), media_type="text/plain")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ================= FILE UPLOAD =================

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    os.makedirs("static/uploads", exist_ok=True)
    file_path = f"static/uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"message": "File uploaded"}
