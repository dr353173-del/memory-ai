import os
import asyncio
from google import genai
from memory import get_memory, save_memory
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("✅ Gemini AI Connected!")
else:
    client = None
    print("⚠️ GEMINI_API_KEY missing!")

# ✅ NEW MODELS (2025 working ones)
MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


def extract_memory(message: str, memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower()
    
    # Multi-line message ko split kar (har line alag process)
    lines = [line.strip() for line in message.split('\n') if line.strip()]
    
    for line in lines:
        line_lower = line.lower()
        
        # Name extraction
        name_triggers = ["mera naam", "my name is", "naam hai"]
        for trigger in name_triggers:
            if trigger in line_lower:
                words = line.split()
                for i, word in enumerate(words):
                    if word.lower() in ["naam", "name", "hai"] and i + 1 < len(words):
                        name = words[i + 1].strip(".,!?")
                        if len(name) > 1 and name.isalpha():
                            updated["name"] = name.capitalize()
                            break
                break
        
        # Age
        if any(t in line_lower for t in ["meri age", "meri umar", "saal ka", "my age"]):
            for word in line.split():
                if word.isdigit() and 5 <= int(word) <= 100:
                    updated["age"] = word
                    break
        
        # Work (only short lines)
        if len(line) < 60:
            work_keywords = ["developer", "engineer", "student", "designer", 
                           "teacher", "doctor", "programmer", "freelancer"]
            for keyword in work_keywords:
                if keyword in line_lower:
                    updated["work"] = line[:50]
                    break
        
        # Hobby
        if len(line) < 60:
            hobby_triggers = ["mera hobby", "my hobby", "i love", "mujhe pasand hai"]
            for trigger in hobby_triggers:
                if trigger in line_lower:
                    updated["hobby"] = line[:50]
                    break
        
        # Food
        if len(line) < 60:
            food_triggers = ["favourite food", "favorite food", "khana pasand", "love eating"]
            for trigger in food_triggers:
                if trigger in line_lower:
                    updated["favorite_food"] = line[:50]
                    break
    
    return updated


async def call_gemini(prompt: str) -> str:
    for model_name in MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": 0.7,
                        "max_output_tokens": 300,
                    }
                )
                reply = response.text.strip()
                print(f"✅ {model_name} (attempt {attempt+1})")
                return reply

            except Exception as e:
                err = str(e)
                if "404" in err:
                    print(f"❌ {model_name} not available")
                    break
                if "429" in err:
                    print(f"⏭️ {model_name} quota over")
                    break
                if "503" in err or "UNAVAILABLE" in err:
                    if attempt < 1:
                        print(f"⏳ {model_name} busy, retry...")
                        await asyncio.sleep(2)
                        continue
                    break
                print(f"⚠️ {model_name}: {err[:80]}")
                break
    
    return None


async def process_message(user_id: str, message: str) -> dict:
    memory = get_memory(user_id)
    new_info = extract_memory(message, memory)
    memory_saved = False

    if new_info:
        memory = {**memory, **new_info}
        save_memory(user_id, memory)
        memory_saved = True
        print(f"💾 Saved: {new_info}")

    info_parts = []
    if memory.get("name"): info_parts.append(f"Name: {memory['name']}")
    if memory.get("age"): info_parts.append(f"Age: {memory['age']}")
    if memory.get("work"): info_parts.append(f"Work: {memory['work']}")
    if memory.get("hobby"): info_parts.append(f"Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): info_parts.append(f"Food: {memory['favorite_food']}")

    memory_text = "\n".join(info_parts) if info_parts else "Koi info nahi abhi"

    prompt = f"""Tu "Memory AI" hai - Deepu ka banaya hua smart AI assistant.

USER KI SAVED INFO:
{memory_text}

RULES:
- User ki language mein reply kar (Hindi/English/Hinglish)
- 2-3 lines mein reply (jab tak lamba na maange)
- Max 1-2 emojis
- Naam pata ho toh use kar
- Saved info ko naturally use kar
- Helpful, warm, friendly reh

User: {message}
Assistant:"""

    reply = None
    if client:
        reply = await call_gemini(prompt)

    if not reply:
        reply = smart_fallback(message, memory)

    return {
        "reply": reply,
        "memory_saved": memory_saved,
        "memory": memory
    }


def smart_fallback(message: str, memory: dict) -> str:
    name = memory.get("name", "")
    work = memory.get("work", "")
    msg = message.lower().strip()

    if any(w in msg for w in ["hi", "hello", "hey", "namaste"]):
        return f"Hey {name}! Kaise ho? 😊" if name else "Hey! Kaise ho? 😊"

    if any(w in msg for w in ["kya hoon", "kya karta", "who am i", "ma kya", "mera kaam"]):
        if work:
            return f"Tum {work} ho! Mujhe yaad hai 💡"
        return "Abhi tumhara kaam mujhe nahi pata. Batao na! 😊"

    if any(w in msg for w in ["naam", "name", "kaun"]):
        if name:
            return f"Tumhara naam {name} hai! Mujhe yaad hai 🧠"
        return "Tumhara naam nahi pata abhi. Batao! 😊"

    if any(w in msg for w in ["thanks", "shukriya"]):
        return f"Welcome {name}! 🙌" if name else "Welcome! 🙌"

    if any(w in msg for w in ["ok", "okay", "thik"]):
        return "Cool! Aur kuch puchna ho toh batao 😊"

    return "Server thoda slow hai. 30 sec baad try karo! ⏰"
