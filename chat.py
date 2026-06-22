# chat.py — Memory AI Pro (Auto-Fallback + Fast)
import os
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

# Models in priority order (fastest + most available first)
MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
]

# ═══════════════════════════════════
#       MEMORY EXTRACT
# ═══════════════════════════════════
def extract_memory_from_message(message: str, current_memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower()

    # NAME detect
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

    # AGE detect
    if any(t in msg_lower for t in ["meri age", "meri umar", "years old", "saal ka", "my age"]):
        words = message.split()
        for word in words:
            if word.isdigit() and 5 <= int(word) <= 100:
                updated["age"] = word
                break

    # WORK detect
    work_triggers = ["kaam karta", "job hai", "work karta", "i work", "developer",
                     "engineer", "student", "designer", "teacher", "doctor", "i am a", "main ek"]
    for trigger in work_triggers:
        if trigger in msg_lower:
            updated["work"] = message[:80]
            break

    # HOBBY detect
    hobby_triggers = ["hobby", "mujhe pasand", "i like", "i love",
                      "acha lagta", "enjoy karta", "khelta hoon"]
    for trigger in hobby_triggers:
        if trigger in msg_lower:
            updated["hobby"] = message[:80]
            break

    # FOOD detect
    food_triggers = ["favourite food", "favorite food", "khana pasand",
                     "mujhe khana", "pasandida khana", "love eating"]
    for trigger in food_triggers:
        if trigger in msg_lower:
            updated["favorite_food"] = message[:80]
            break

    return updated

# ═══════════════════════════════════
#       MAIN PROCESS FUNCTION
# ═══════════════════════════════════
async def process_message(user_id: str, message: str) -> dict:
    # Step 1: Memory load
    memory = get_memory(user_id)

    # Step 2: Extract new info
    new_info = extract_memory_from_message(message, memory)
    memory_saved = False

    # Step 3: Save if new
    if new_info:
        updated_memory = {**memory, **new_info}
        save_memory(user_id, updated_memory)
        memory = updated_memory
        memory_saved = True
        print(f"💾 Memory Updated: {new_info}")

    # Step 4: User info text
    user_info = []
    if memory.get("name"): user_info.append(f"- Name: {memory['name']}")
    if memory.get("age"): user_info.append(f"- Age: {memory['age']}")
    if memory.get("work"): user_info.append(f"- Work: {memory['work']}")
    if memory.get("hobby"): user_info.append(f"- Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): user_info.append(f"- Favorite Food: {memory['favorite_food']}")

    user_info_text = "\n".join(user_info) if user_info else "No info yet"

    # Step 5: SHORT SMART PROMPT (Fast)
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

    # Step 6: AUTO-FALLBACK GEMINI CALL
    reply = None
    
    if client:
        full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
        
        for model_name in MODELS:
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
                print(f"✅ Reply from: {model_name}")
                break  # Success! Stop trying
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ {model_name} failed: {error_msg[:100]}")
                continue  # Try next model
        
        if not reply:
            print("❌ All models failed, using fallback")
            reply = fallback_reply(message, memory)
    else:
        reply = fallback_reply(message, memory)

    return {
        "reply": reply,
        "memory_saved": memory_saved,
        "memory": memory
    }

# ═══════════════════════════════════
#       FALLBACK (No Gemini)
# ═══════════════════════════════════
def fallback_reply(message: str, memory: dict) -> str:
    name = memory.get("name", "")
    greeting = f"Hey {name}! " if name else "Hey! "
    msg_lower = message.lower()

    if any(w in msg_lower for w in ["hello", "hi", "hey", "namaste"]):
        return f"{greeting}Kaise ho? Main tumhara Memory AI hoon! 🧠"
    elif any(w in msg_lower for w in ["naam", "name", "yaad"]):
        if name:
            return f"Haan! Tumhara naam **{name}** hai! Mujhe yaad hai! 🧠"
        return "Abhi tumhara naam nahi pata. Batao apna naam! 😊"
    elif any(w in msg_lower for w in ["thanks", "shukriya", "thank you"]):
        return f"Koi baat nahi {name}! Hamesha yahan hoon! 🙌"
    else:
        return f"{greeting}Server thoda busy hai, ek second mein try kar! 😊"
