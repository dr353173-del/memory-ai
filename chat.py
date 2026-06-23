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

# Fast models pehle
MODELS = [
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
]

def extract_memory(message: str, memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower()

    # Name
    name_triggers = ["mera naam", "my name is", "i am", "main hoon", "naam hai", "naam deepu", "naam rahul"]
    for trigger in name_triggers:
        if trigger in msg_lower:
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() in ["naam", "name", "am", "hoon", "hai"] and i + 1 < len(words):
                    name = words[i + 1].strip(".,!?")
                    if len(name) > 1:
                        updated["name"] = name.capitalize()
                        break

    # Age
    if any(t in msg_lower for t in ["meri age", "meri umar", "years old", "saal ka", "my age"]):
        for word in message.split():
            if word.isdigit() and 5 <= int(word) <= 100:
                updated["age"] = word
                break

    # Work
    work_triggers = ["developer", "engineer", "student", "designer", "teacher", 
                     "doctor", "kaam karta", "job hai", "work karta", "i work",
                     "i am a", "main ek", "hoon main", "hoon ek"]
    for trigger in work_triggers:
        if trigger in msg_lower:
            updated["work"] = message[:100]
            break

    # Hobby
    hobby_triggers = ["hobby", "mujhe pasand", "i like", "i love", "khelta hoon", "padhna", "gaming"]
    for trigger in hobby_triggers:
        if trigger in msg_lower:
            updated["hobby"] = message[:100]
            break

    # Food
    food_triggers = ["favourite food", "favorite food", "khana pasand", "love eating", "pasandida"]
    for trigger in food_triggers:
        if trigger in msg_lower:
            updated["favorite_food"] = message[:100]
            break

    return updated


async def call_gemini(prompt: str) -> str:
    for model_name in MODELS:
        for attempt in range(3):  # 3 retries per model
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
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"⏭️ {model_name} quota over")
                    break
                if "503" in err or "UNAVAILABLE" in err:
                    if attempt < 2:
                        print(f"⏳ {model_name} busy, retry {attempt+1}...")
                        await asyncio.sleep(3)
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

    # Memory context banana
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
- Saved info ko naturally use kar conversation mein
- Helpful, warm aur friendly reh

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

    if any(w in msg for w in ["kya hoon", "kya ho", "kya karta", "who am i", "ma kya", "mera kaam"]):
        if work:
            return f"Tumhari info mein hai: {work} 💡"
        return "Abhi tumhara kaam mujhe nahi pata. Batao na! 😊"

    if any(w in msg for w in ["naam", "name", "kaun"]):
        if name:
            return f"Tumhara naam {name} hai! Mujhe yaad hai 🧠"
        return "Tumhara naam nahi pata abhi. Batao! 😊"

    if any(w in msg for w in ["thanks", "shukriya", "thank"]):
        return f"Welcome {name}! 🙌" if name else "Welcome! 🙌"

    if any(w in msg for w in ["ok", "okay", "thik", "accha"]):
        return f"Cool! Aur kuch puchna ho toh batao 😊"

    if any(w in msg for w in ["aur tum", "tum kaisa", "how are you", "aur aap"]):
        return "Main ekdum fit hoon! Tera AI hoon na 😄 Tu bata kya chal raha hai?"

    # Default
    return "Abhi Gemini server thoda busy hai. 30 sec baad try karo! ⏰"
