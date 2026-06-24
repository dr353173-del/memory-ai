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
    chat_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    chat_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
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
- If user writes in pure Hindi (Devanagari) → reply in pure Hindi.
- If user writes in Hinglish → reply in Hinglish.
- NEVER mix languages unless user mixes them.

🔴 FORMATTING RULES (VERY IMPORTANT):
- DO NOT use markdown symbols like **, ##, ###, ***, __, ~~, ```
- DO NOT use bold/italic markdown.
- Write in plain natural text only.
- For lists, use simple format like:
  1. First point
  2. Second point
  OR use dashes:
  - Point one
  - Point two
- For emphasis, just write naturally — don't use asterisks.
- Keep text clean and readable like a human writing.

PROFESSIONAL RULES:
1. Give structured, detailed answers.
2. Use simple numbered lists or dashes when needed.
3. Think step-by-step before answering.
4. Never give short lazy answers.
5. Write like a smart human, not a robot.

MEMORY RULES:
1. ALWAYS remember past conversations.
2. Use user's name, work, hobby, food naturally.
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
    chat_id: str = "default"
    message: str

class ExtractRequest(BaseModel):
    user_id: str = "default"

class ChatListRequest(BaseModel):
    user_id: str

class DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str

class MessagesRequest(BaseModel):
    user_id: str
    chat_id: str

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
        chat_id = req.chat_id
        message = req.message

        if not message:
            return JSONResponse({"error": "Empty message"}, status_code=400)

        cursor.execute("SELECT chat_id FROM chats WHERE chat_id = ?", (chat_id,))
        if not cursor.fetchone():
            title = message[:40] + ("..." if len(message) > 40 else "")
            cursor.execute(
                "INSERT INTO chats (chat_id, user_id, title, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, title, datetime.utcnow().isoformat())
            )
            conn.commit()

        cursor.execute(
            "INSERT INTO messages (user_id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, chat_id, "user", message, datetime.utcnow().isoformat())
        )
        conn.commit()

        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ? AND chat_id = ?
            ORDER BY id DESC
            LIMIT 20
        """, (user_id, chat_id))
        rows = cursor.fetchall()
        rows.reverse()

        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,))
        memory_rows = cursor.fetchall()

        memory_context = "\n".join([f"{r[0]}: {r[1]}" for r in memory_rows[-5:]])

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"User's recent memory across all chats:\n{memory_context}"}
        ]
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
                "INSERT INTO messages (user_id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, chat_id, "assistant", full_response, datetime.utcnow().isoformat())
            )
            conn.commit()

        return StreamingResponse(stream(), media_type="text/plain")

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/chats")
async def get_chats(req: ChatListRequest):
    try:
        cursor.execute("""
            SELECT chat_id, title, created_at FROM chats
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (req.user_id,))
        rows = cursor.fetchall()
        return [{"chat_id": r[0], "title": r[1], "created_at": r[2]} for r in rows]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/messages")
async def get_messages(req: MessagesRequest):
    try:
        cursor.execute("""
            SELECT role, content FROM messages
            WHERE user_id = ? AND chat_id = ?
            ORDER BY id ASC
        """, (req.user_id, req.chat_id))
        rows = cursor.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/delete-chat")
async def delete_chat(req: DeleteChatRequest):
    try:
        cursor.execute("DELETE FROM messages WHERE user_id = ? AND chat_id = ?",
                       (req.user_id, req.chat_id))
        cursor.execute("DELETE FROM chats WHERE user_id = ? AND chat_id = ?",
                       (req.user_id, req.chat_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/extract-info")
async def extract_info(req: ExtractRequest):
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
Analyze this chat and extract ONLY these about the USER:
1. Name
2. Work / Profession
3. Hobby
4. Favorite Food

Reply ONLY in JSON format:
{{"name": "", "work": "", "hobby": "", "food": ""}}

If not mentioned, leave empty "".
Keep values SHORT (1-3 words).

Chat:
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
        if "```" in result:
            result = result.split("```")[1].replace("json", "").strip()

        data = json.loads(result)

        cursor.execute("""
            INSERT OR REPLACE INTO profile (user_id, name, work, hobby, food)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, data.get("name", ""), data.get("work", ""),
              data.get("hobby", ""), data.get("food", "")))
        conn.commit()

        return data

    except Exception as e:
        return {"name": "", "work": "", "hobby": "", "food": "", "error": str(e)}
