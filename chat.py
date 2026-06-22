# chat.py — Memory AI Pro (Multi-Language Support)

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


# ═══════════════════════════════════
#       MEMORY EXTRACT
# ═══════════════════════════════════
def extract_memory_from_message(message: str, current_memory: dict) -> dict:
    """User ke message se information extract karo"""
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
                     "engineer", "student", "designer", "teacher", "doctor", "banata hoon",
                     "i am a", "main ek"]
    for trigger in work_triggers:
        if trigger in msg_lower:
            updated["work"] = message[:80]
            break

    # HOBBY detect
    hobby_triggers = ["hobby", "mujhe pasand", "i like", "i love",
                      "acha lagta", "enjoy karta", "khelta hoon", "passionate about"]
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
    """Main function — message process karo aur reply do"""

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

    # Step 4: User info text banao
    user_info = []
    if memory.get("name"):
        user_info.append(f"- Name: {memory['name']}")
    if memory.get("age"):
        user_info.append(f"- Age: {memory['age']}")
    if memory.get("work"):
        user_info.append(f"- Work: {memory['work']}")
    if memory.get("hobby"):
        user_info.append(f"- Hobby: {memory['hobby']}")
    if memory.get("favorite_food"):
        user_info.append(f"- Favorite Food: {memory['favorite_food']}")

    user_info_text = "\n".join(user_info) if user_info else "No info yet about user"

    # Step 5: SMART MULTI-LANGUAGE SYSTEM PROMPT
    system_prompt = f"""You are "Memory AI" — a smart, friendly AI assistant who remembers user information.

═══════════════════════════════
👤 USER INFO (REMEMBER THIS)
═══════════════════════════════
{user_info_text}

═══════════════════════════════
🌍 LANGUAGE INTELLIGENCE (TOP PRIORITY)
═══════════════════════════════
DETECT the language user is typing in, and RESPOND in the EXACT SAME language:

- Hindi (हिंदी) → Reply in pure Hindi
- English → Reply in pure English  
- Hinglish (Hindi + English mix) → Reply in Hinglish
- Punjabi → Reply in Punjabi
- Marathi / Gujarati / Tamil / Bengali / Telugu → Match user's language
- Technical / Coding queries → Use clear English

⚠️ NEVER force Hinglish on English speakers!
⚠️ NEVER force English on Hindi speakers!
⚠️ Always MATCH the user's language style!

═══════════════════════════════
🎯 RESPONSE STYLE
═══════════════════════════════
TONE: Friendly, casual, warm — like talking to a close friend
LENGTH: 2-4 lines normally; longer ONLY when user asks for details
EMOJIS: Use sparingly (1-2 per message max)
NAME: Use user's name if you know it

═══════════════════════════════
💡 SPECIAL BEHAVIORS
═══════════════════════════════
- Coding/Tech question → Give code + clear explanation in English
- Personal chat → Be casual, warm, friendly
- Question about memory → Reference saved info naturally
- Greeting → Warm welcome using name if known
- Sad/upset user → Be empathetic and supportive
- Question about you → You're "Memory AI" built by Deepu

═══════════════════════════════
✅ DO
═══════════════════════════════
- Match user's language PERFECTLY
- Use saved memory naturally in conversation
- Be helpful, clear, and direct
- Show personality and warmth

═══════════════════════════════
❌ DON'T
═══════════════════════════════
- Don't force any specific language
- Don't use too many emojis
- Don't give robotic responses
- Don't ignore user's language preference
- Don't make responses too long unless asked
"""

    # Step 6: Gemini reply
    if client:
        try:
            full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=full_prompt
            )
            reply = response.text.strip()
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
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
    """Agar Gemini available nahi hai"""
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
        return f"{greeting}Batao, kya help chahiye? 😊"
