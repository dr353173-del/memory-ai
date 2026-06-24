import os
import json
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS profile (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    work TEXT,
    hobby TEXT,
    food TEXT
)
""")
conn.commit()

# ================= SYSTEM PROMPT =================

SYSTEM_PROMPT = """
You are Memory AI Pro — built by Deepu.
You are a highly professional, intelligent AI assistant like ChatGPT.

🔴 MOST IMPORTANT LANGUAGE RULE:
- Detect the language of the user's LATEST message and reply in the SAME language.
- If user writes in English → reply 100% in English.
- If user writes in pure Hindi (Devanagari script) → reply in pure Hindi.
- If user writes in Hinglish (Roman Hindi like "kaise ho", "batao") → reply in Hinglish.
- NEVER mix languages unless user mixes them.

PROFESSIONAL RULES:
1. Give structured, detailed answers like ChatGPT.
2. Use headings, bullet points, numbered lists when needed.
3. Think step-by-step before answering.
4. Never give short lazy answers.

MEMORY RULES:
1. ALWAYS remember past conversations.
2. Use user's name, work, hobby, food preference naturally.
3. Reference past chats when relevant.

PERSONALITY:
- Friendly but professional.
- In Hinglish, use "bhai", "yaar" naturally.
- In English, stay professional.
- In Hindi, use respectful Hindi.

Built by Deepu. Version 1.0.
"""

# ================= MODELS =================

class ChatRequest(BaseModel):
    user_id: str = "default"
    message: str

class ExtractRequest(BaseModel):
    user_id: str = "default"

# ================= ROUTES =================

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("manifest.json")

@app.get("/service-worker.js")
async def sw():
    return FileResponse("service-worker.js", media_type="application/javascript")

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


@app.post("/extract-info")
async def extract_info(req: ExtractRequest):
    """Extract name, work, hobby, food from chat history"""
    try:
        user_id = req.user_id

        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 30
        """, (user_id,))
        rows = cursor.fetchall()
        rows.reverse()

        if not rows:
            return {"name": "", "work": "", "hobby": "", "food": ""}

        chat_text = "\n".join([f"{r[0]}: {r[1]}" for r in rows])

        extract_prompt = f"""
Analyze this chat history and extract ONLY these 4 things about the USER:
1. Name
2. Work / Profession
3. Hobby
4. Favorite Food

Reply ONLY in this exact JSON format (no extra text):
{{"name": "", "work": "", "hobby": "", "food": ""}}

If something is not mentioned, leave it empty "".
Keep values SHORT (1-3 words max).

Chat history:
{chat_text}
"""

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a JSON extractor. Reply only with valid JSON."},
                {"role": "user", "content": extract_prompt}
            ],
            temperature=0.1
        )

        result = completion.choices[0].message.content.strip()

        # Clean response
        if "```" in result:
            result = result.split("```")[1].replace("json", "").strip()

        data = json.loads(result)

        # Save to profile
        cursor.execute("""
            INSERT OR REPLACE INTO profile (user_id, name, work, hobby, food)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, data.get("name", ""), data.get("work", ""), 
              data.get("hobby", ""), data.get("food", "")))
        conn.commit()

        return data

    except Exception as e:
        return {"name": "", "work": "", "hobby": "", "food": "", "error": str(e)}
