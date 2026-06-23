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

# ⚡ FAST MODELS ONLY (skip slow ones)
MODELS = [
    "gemini-2.0-flash-lite",   # Fastest ⚡
    "gemini-2.0-flash",         # Fast backup
    "gemini-2.5-flash",         # Last resort
]


def extract_memory(message: str, memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower().strip()
    
    # NAME
    name_patterns = ["mera naam", "my name is", "naam hai", "i am", "main hoon"]
    for pattern in name_patterns:
        if pattern in msg_lower:
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ["naam", "name", "am", "hai"] and i + 1 < len(words):
                    name = words[i + 1].strip(".,!?")
                    if len(name) >= 2 and name.replace(" ", "").isalpha():
                        updated["name"] = name.capitalize()
                        break
            break
    
    # AGE
    age_keywords = ["saal", "age", "umar", "years old"]
    if any(k in msg_lower for k in age_keywords):
        for word in message.split():
            clean = word.strip(".,!?")
            if clean.isdigit() and 5 <= int(clean) <= 100:
                updated["age"] = clean
                break
    
    # WORK
    work_map = {
        "developer": "Developer", "engineer": "Engineer", "student": "Student",
        "designer": "Designer", "teacher": "Teacher", "doctor": "Doctor",
        "programmer": "Programmer", "freelancer": "Freelancer", "businessman": "Businessman",
    }
    for keyword, label in work_map.items():
        if keyword in msg_lower:
            updated["work"] = label
            break
    
    # HOBBY
    hobby_map = {
        "gaming": "Gaming", "padhna": "Reading", "reading": "Reading",
        "music": "Music", "cricket": "Cricket", "football": "Football",
        "coding": "Coding", "movies": "Movies", "travel": "Travelling",
    }
    if any(t in msg_lower for t in ["hobby", "pasand", "i love", "i like", "shauq"]):
        for keyword, label in hobby_map.items():
            if keyword in msg_lower:
                updated["hobby"] = label
                break
    
    # FOOD
    food_map = {
        "pizza": "Pizza", "burger": "Burger", "biryani": "Biryani",
        "samosa": "Samosa", "pasta": "Pasta", "chinese": "Chinese",
        "dosa": "Dosa", "rajma": "Rajma Chawal",
    }
    if any(t in msg_lower for t in ["food", "khana", "favourite", "favorite", "pasand"]):
        for keyword, label in food_map.items():
            if keyword in msg_lower:
                updated["favorite_food"] = label
                break
    
    return updated


async def call_gemini(prompt: str) -> str:
    """⚡ Fast call - 1 retry per model, short wait"""
    for model_name in MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": 0.7,
                        "max_output_tokens": 200,  # Shorter = faster
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
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    if attempt < 1:
                        print(f"⏳ {model_name} rate limit, wait 2s...")
                        await asyncio.sleep(2)
                        continue
                    break
                if "503" in err or "UNAVAILABLE" in err:
                    if attempt < 1:
                        print(f"⏳ {model_name} busy, retry...")
                        await asyncio.sleep(1)
                        continue
                    break
                print(f"⚠️ {model_name}: {err[:60]}")
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
    if memory.get("age"): info_parts.append(f"Age: {memory['age']} years")
    if memory.get("work"): info_parts.append(f"Work: {memory['work']}")
    if memory.get("hobby"): info_parts.append(f"Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): info_parts.append(f"Food: {memory['favorite_food']}")

    memory_text = "\n".join(info_parts) if info_parts else "No info yet"

    # ⚡ SHORTER PROMPT = FASTER
    prompt = f"""You are Memory AI by Deepu. Reply in user's language. Be short (1-2 lines), friendly, use 1-2 emojis.

User Info:
{memory_text}

User: {message}
Reply:"""

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
    age = memory.get("age", "")
    hobby = memory.get("hobby", "")
    food = memory.get("favorite_food", "")
    msg = message.lower().strip()

    if any(w in msg for w in ["hi", "hello", "hey", "namaste", "hii"]):
        return f"Hey {name}! Kaise ho? 😊" if name else "Hey! Kaise ho? 😊"

    if any(w in msg for w in ["tum kaun", "who are you", "aap kaun"]):
        return "Main Memory AI hoon — tera personal AI by Deepu 🤖"

    if any(w in msg for w in ["mera naam", "my name", "kya naam"]):
        return f"Tera naam {name} hai! 🧠" if name else "Naam abhi nahi pata. Batao! 😊"

    if any(w in msg for w in ["mera kaam", "my work", "kya karta", "kaam kya"]):
        return f"Tu {work} hai! 💼" if work else "Kaam nahi pata. Batao! 😊"

    if any(w in msg for w in ["meri age", "my age", "kitne saal", "umar"]):
        return f"Tu {age} saal ka hai! 🎂" if age else "Age nahi pata. Batao! 😊"

    if any(w in msg for w in ["meri hobby", "my hobby", "shauq"]):
        return f"Teri hobby {hobby} hai! 🎯" if hobby else "Hobby nahi pata. Batao! 😊"

    if any(w in msg for w in ["mera favourite", "favorite food", "kya khana"]):
        return f"Tujhe {food} pasand hai! 🍕" if food else "Food nahi pata. Batao! 😊"

    if any(w in msg for w in ["sab batao", "mere baare", "about me"]):
        info = []
        if name: info.append(f"Naam: {name}")
        if age: info.append(f"Age: {age}")
        if work: info.append(f"Kaam: {work}")
        if hobby: info.append(f"Hobby: {hobby}")
        if food: info.append(f"Food: {food}")
        if info:
            return "Ye sab pata hai:\n" + "\n".join(f"• {i}" for i in info) + " 🧠"
        return "Tere baare mein kuch nahi pata. Batao! 😊"

    if any(w in msg for w in ["thanks", "shukriya"]):
        return f"Welcome {name}! 🙌" if name else "Welcome! 🙌"

    if msg in ["ok", "okay", "thik", "accha", "haan", "hmm"]:
        return "Cool! Aur kuch puchna ho toh batao 😊"

    return f"{name}, AI thoda busy. 5 sec baad try kar! ⏰" if name else "AI busy. 5 sec baad try kar! ⏰"
