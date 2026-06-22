# chat.py — Memory AI Pro (Smart Retry + Auto-Fallback)
import os
import time
import asyncio
from google import genai
from memory import get_memory, save_memory
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════
#       GEMINI SETUP
# ═══════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("✅ Gemini AI Connected! (New SDK)")
else:
    client = None
    print("⚠️ GEMINI_API_KEY not found in .env")

# Models in priority order (fastest + most reliable first)
MODELS = [
    "gemini-1.5-flash-8b",      # Sabse fast + stable
    "gemini-1.5-flash",          # Backup 1
    "gemini-2.0-flash-exp",      # Backup 2
    "gemini-1.5-pro",            # Last resort
]

MAX_RETRIES = 2  # Each model 2 baar try karega
RETRY_DELAY = 2  # 2 second wait between retries

# ═══════════════════════════════════
#       MEMORY EXTRACT
# ═══════════════════════════════════
def extract_memory_from_message(message: str, current_memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower()

    name_triggers = ["mera naam", "my name is", "i am", "main hoon", "naam hai"]
    for trigger in name_triggers:
        if trigger in msg_lower:
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ["naam", "name", "am", "hoon", "hai"] and i + 1 < len(words):
                    name = words[i + 1].strip(".,!?")
                    if len(name) > 1 and name.isalpha():
                        updated["name"] = name.capitalize()
                        break

    if any(t in msg_lower for t in ["meri age", "meri umar", "years old", "saal ka", "my age"]):
        words = message.split()
        for word in words:
            if word.isdigit() and 5 <= int(word) <= 100:
                updated["age"] = word
                break

    work_triggers = ["kaam karta", "job hai", "work karta", "i work", "developer",
                     "engineer", "student", "designer", "teacher", "doctor", "i am a", "main ek"]
    for trigger in work_triggers:
        if trigger in msg_lower:
            updated["work"] = message[:80]
            break

    hobby_triggers = ["hobby", "mujhe pasand", "i like", "i love",
                      "acha lagta", "enjoy karta", "khelta hoon"]
    for trigger in hobby_triggers:
        if trigger in msg_lower:
            updated["hobby"] = message[:80]
            break

    food_triggers = ["favourite food", "favorite food", "khana pasand",
                     "mujhe khana", "pasandida khana", "love eating"]
    for trigger in food_triggers:
        if trigger in msg_lower:
            updated["favorite_food"] = message[:80]
            break

    return updated

# ═══════════════════════════════════
#       GEMINI CALL WITH RETRY
# ═══════════════════════════════════
async def call_gemini_with_retry(full_prompt: str) -> str:
    """Smart retry — har model ko multiple times try karo"""
    
    for model_name in MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config={
                        "temperature": 0.7,
                        "max_output_tokens": 250,
                        "top_p": 0.9
                    }
                )
                reply = response.text.strip()
                print(f"✅ Success: {model_name} (attempt {attempt + 1})")
                return reply
            
            except Exception as e:
                error_msg = str(e)
                
                # If quota exceeded (429) → skip this model entirely
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"⏭️ {model_name} quota exceeded, trying next model")
                    break  # Try next model
                
                # If server busy (503) → retry same model
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    if attempt < MAX_RETRIES - 1:
                        print(f"⏳ {model_name} busy, retrying in {RETRY_DELAY}s...")
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    else:
                        print(f"❌ {model_name} failed after {MAX_RETRIES} attempts")
                        break  # Try next model
                
                # Any other error → try next model
                print(f"⚠️ {model_name} error: {error_msg[:80]}")
                break
    
    return None  # All models failed

# ═══════════════════════════════════
#       MAIN PROCESS FUNCTION
# ═══════════════════════════════════
async def process_message(user_id: str, message: str) -> dict:
    memory = get_memory(user_id)
    new_info = extract_memory_from_message(message, memory)
    memory_saved = False

    if new_info:
        updated_memory = {**memory, **new_info}
        save_memory(user_id, updated_memory)
        memory = updated_memory
        memory_saved = True
        print(f"💾 Memory Updated: {new_info}")

    user_info = []
    if memory.get("name"): user_info.append(f"- Name: {memory['name']}")
    if memory.get("age"): user_info.append(f"- Age: {memory['age']}")
    if memory.get("work"): user_info.append(f"- Work: {memory['work']}")
    if memory.get("hobby"): user_info.append(f"- Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): user_info.append(f"- Favorite Food: {memory['favorite_food']}")

    user_info_text = "\n".join(user_info) if user_info else "No info yet"

    system_prompt = f"""You are "Memory AI" by Deepu - friendly assistant who remembers users.

👤 USER INFO:
{user_info_text}

🌍 RULES:
- Reply in user's EXACT language (Hindi/English/Hinglish/Punjabi etc)
- 2-3 lines only (longer if user asks)
- 1-2 emojis max
- Use user's name if known
- Code questions → English with examples
- Reference saved memory naturally
- Be warm, friendly, direct, helpful"""

    reply = None
    if client:
        full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
        reply = await call_gemini_with_retry(full_prompt)
    
    if not reply:
        print("❌ All Gemini models failed, using smart fallback")
        reply = smart_fallback(message, memory)

    return {
        "reply": reply,
        "memory_saved": memory_saved,
        "memory": memory
    }

# ═══════════════════════════════════
#       SMART FALLBACK
# ═══════════════════════════════════
def smart_fallback(message: str, memory: dict) -> str:
    """Better fallback - context-aware replies"""
    name = memory.get("name", "")
    greeting = f"{name}, " if name else ""
    msg_lower = message.lower()

    # Greetings
    if any(w in msg_lower for w in ["hello", "hi", "hey", "namaste", "hii"]):
        return f"Hey {name}! Kaise ho? 😊"
    
    # Name questions
    elif any(w in msg_lower for w in ["mera naam", "my name", "kya naam"]):
        if name:
            return f"Tumhara naam **{name}** hai! Mujhe yaad hai 🧠✨"
        return "Abhi tumhara naam nahi pata. Batao na! 😊"
    
    # Thanks
    elif any(w in msg_lower for w in ["thanks", "shukriya", "thank you", "thx"]):
        return f"Welcome {name}! Hamesha yahan hoon 🙌"
    
    # Help / Need help
    elif any(w in msg_lower for w in ["help", "madad", "need"]):
        return f"{greeting}bilkul! Batao kya help chahiye? 💪"
    
    # OK / Acknowledgment
    elif msg_lower.strip() in ["ok", "okay", "k", "hmm", "haan", "yes"]:
        return f"Cool {name}! Aur kuch puchna ho toh batao 😊"
    
    # Generic — but contextual
    else:
        return f"{greeting}Gemini server pe load zyada hai abhi. 30 second baad try kar! ⏰"
