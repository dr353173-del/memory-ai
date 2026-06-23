import os
import asyncio
from groq import Groq
from memory import get_memory, save_memory
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq AI Connected! ⚡")
else:
    client = None
    print("⚠️ GROQ_API_KEY missing!")

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

# Question words — inhe naam mat banao
QUESTION_WORDS = ["kya", "what", "kaun", "who", "kaisa", "how", "kaisi", "konsa", "kahan", "where", "kab", "when"]


def extract_memory(message: str, memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower().strip()
    
    # Check if it's a question
    is_question = "?" in message or any(qw in msg_lower.split()[:3] for qw in QUESTION_WORDS)
    
    # ✅ NAME (only if NOT a question)
    if not is_question:
        name_patterns = ["mera naam", "my name is", "naam hai", "i am", "main hoon"]
        for pattern in name_patterns:
            if pattern in msg_lower:
                words = message.split()
                for i, word in enumerate(words):
                    if word.lower() in ["naam", "name", "am", "hai"] and i + 1 < len(words):
                        candidate = words[i + 1].strip(".,!?")
                        if (len(candidate) >= 2 
                            and candidate.replace(" ", "").isalpha() 
                            and candidate.lower() not in QUESTION_WORDS):
                            updated["name"] = candidate.capitalize()
                            break
                break
    
    # ✅ AGE (only if NOT a question or has clear number)
    age_keywords = ["saal", "age", "umar", "years old"]
    if any(k in msg_lower for k in age_keywords) and not is_question:
        for word in message.split():
            clean = word.strip(".,!?")
            if clean.isdigit() and 5 <= int(clean) <= 100:
                updated["age"] = clean
                break
    
    # ✅ WORK (only statements)
    if not is_question:
        work_map = {
            "developer": "Developer", "engineer": "Engineer", "student": "Student",
            "designer": "Designer", "teacher": "Teacher", "doctor": "Doctor",
            "programmer": "Programmer", "freelancer": "Freelancer", "businessman": "Businessman",
        }
        for keyword, label in work_map.items():
            if keyword in msg_lower:
                updated["work"] = label
                break
    
    # ✅ HOBBY (only statements)
    if not is_question:
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
    
    # ✅ FOOD (only statements)
    if not is_question:
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


async def call_groq(prompt: str, system_prompt: str) -> str:
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=250,
            )
            reply = response.choices[0].message.content.strip()
            print(f"⚡ {model_name} - SUCCESS")
            return reply
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "429" in err:
                print(f"⏳ {model_name} rate limit, next model...")
                continue
            print(f"⚠️ {model_name}: {err[:80]}")
            continue
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

    system_prompt = f"""You are "Memory AI" - smart friendly AI built by Deepu.

USER'S SAVED INFO:
{memory_text}

RULES:
- Reply in user's EXACT language (Hindi/English/Hinglish)
- Keep replies SHORT (1-3 lines max)
- Use 1-2 emojis only
- Use saved info naturally — answer questions directly
- Be warm, friendly, direct
- If user asks "mera naam kya hai" → directly say their name from saved info"""

    reply = None
    if client:
        reply = await call_groq(message, system_prompt)

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

    if any(w in msg for w in ["hi", "hello", "hey", "namaste"]):
        return f"Hey {name}! Kaise ho? 😊" if name else "Hey! Kaise ho? 😊"

    if any(w in msg for w in ["tum kaun", "who are you", "aap kaun"]):
        return "Main Memory AI hoon — Deepu ka banaya AI 🤖"

    if any(w in msg for w in ["mera naam", "my name", "kya naam"]):
        return f"Tera naam {name} hai! 🧠" if name else "Naam batao na! 😊"

    if any(w in msg for w in ["mera kaam", "kya karta"]):
        return f"Tu {work} hai! 💼" if work else "Kaam batao! 😊"

    if any(w in msg for w in ["meri age", "kitne saal"]):
        return f"Tu {age} saal ka hai! 🎂" if age else "Age batao! 😊"

    if any(w in msg for w in ["meri hobby"]):
        return f"Teri hobby {hobby} hai! 🎯" if hobby else "Hobby batao! 😊"

    if any(w in msg for w in ["mera favourite", "kya khana"]):
        return f"Tujhe {food} pasand hai! 🍕" if food else "Food batao! 😊"

    if any(w in msg for w in ["sab batao", "mere baare"]):
        info = []
        if name: info.append(f"Naam: {name}")
        if age: info.append(f"Age: {age}")
        if work: info.append(f"Kaam: {work}")
        if hobby: info.append(f"Hobby: {hobby}")
        if food: info.append(f"Food: {food}")
        if info:
            return "Tere baare mein:\n" + "\n".join(f"• {i}" for i in info) + " 🧠"
        return "Kuch nahi pata. Batao! 😊"

    if any(w in msg for w in ["thanks", "shukriya"]):
        return f"Welcome {name}! 🙌" if name else "Welcome! 🙌"

    if msg in ["ok", "okay", "thik", "accha"]:
        return "Cool! Aur batao 😊"

    return "AI thoda busy. 5 sec baad try kar! ⏰"
