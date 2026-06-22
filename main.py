from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from chat import process_message
from memory import get_all_memories, delete_memory
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

# ═══════════════════════════════════
#       HOME ROUTE (GET + HEAD)
# ═══════════════════════════════════
@app.get("/")
@app.head("/")
async def home():
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    return FileResponse(file_path)

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
#       MEMORIES ROUTE (GET + HEAD)
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

# ═══════════════════════════════════
#       HEALTH CHECK (GET + HEAD)
# ═══════════════════════════════════
@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok", "message": "Memory AI Pro is running! 🚀"}

# ═══════════════════════════════════
#       PING ROUTES (UptimeRobot)
# ═══════════════════════════════════
@app.get("/ping")
@app.head("/ping")
async def ping():
    return {"status": "alive", "message": "pong! 🏓"}
