from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from chat import process_message
from memory import get_all_memories, delete_memory, reset_database
import os

app = FastAPI(title="Memory AI Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str = "deepu"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════
#       HOME ROUTE
# ═══════════════════════════════════
@app.get("/")
@app.head("/")
async def home():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ═══════════════════════════════════
#       PWA FILES
# ═══════════════════════════════════
@app.get("/manifest.json")
async def manifest():
    return FileResponse(os.path.join(BASE_DIR, "manifest.json"), media_type="application/json")

@app.get("/service-worker.js")
async def service_worker():
    return FileResponse(os.path.join(BASE_DIR, "service-worker.js"), media_type="application/javascript")

@app.get("/icon-192.png")
async def icon_192():
    return FileResponse(os.path.join(BASE_DIR, "icon-192.png"), media_type="image/png")

@app.get("/icon-512.png")
async def icon_512():
    return FileResponse(os.path.join(BASE_DIR, "icon-512.png"), media_type="image/png")

# ═══════════════════════════════════
#       CHAT ROUTE
# ═══════════════════════════════════
@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        result = await process_message(request.user_id, request.message)
        return result
    except Exception as e:
        return {"error": str(e), "reply": "Kuch problem aa gayi! 😕"}

# ═══════════════════════════════════
#       MEMORIES ROUTE
# ═══════════════════════════════════
@app.get("/memories")
@app.head("/memories")
async def memories():
    all_mem = get_all_memories()
    return {"memories": all_mem, "count": len(all_mem)}

@app.delete("/memories/{user_id}")
async def remove_memory(user_id: str):
    success = delete_memory(user_id)
    return {"success": success}

@app.get("/reset-all")
@app.delete("/reset-all")
async def reset_all():
    success = reset_database()
    return {"success": success, "message": "Sab memory clear ho gayi! 🧹"}

# ═══════════════════════════════════
#       HEALTH + PING
# ═══════════════════════════════════
@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok", "message": "Memory AI Pro is running! 🚀"}

@app.get("/ping")
@app.head("/ping")
async def ping():
    return {"status": "alive", "message": "pong! 🏓"}
