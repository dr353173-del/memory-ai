import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq

# ========= CONFIG =========
GROQ_API_KEY = "PASTE_YOUR_GROQ_API_KEY_HERE"
MODEL_NAME = "llama3-70b-8192"

# ========= INIT =========
app = FastAPI()
client = Groq(api_key=GROQ_API_KEY)

templates = Jinja2Templates(directory="templates")

os.makedirs("uploads", exist_ok=True)

# ========= DATABASE =========
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

# ========= HELPERS =========

SYSTEM_PROMPT = """
You are Memory AI Pro — a professional AI assistant like ChatGPT.

Rules:
- Respond clearly and professionally
- Use headings and bullet points when useful
- Give structured answers
- Think step-by-step
- Use past conversation context when relevant
- Avoid unnecessary emojis
"""

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

# ========= ROUTES =========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.post("/chat")
async def chat(request: Request):
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

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}
