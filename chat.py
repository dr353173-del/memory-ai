import os
import re
import asyncio
from groq import Groq
from memory import get_memory, save_memory, delete_memory_field, clear_all_memory
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

QUESTION_WORDS = ["kya", "what", "kaun", "who", "kaisa", "how", "kaisi", "konsa",
                  "kahan", "where", "kab", "when", "kyun", "why", "kitna", "kitne"]

BLOCKED_NAMES = ["bhai", "yaar", "dost", "sir", "madam", "ji", "hello", "hi", "hey",
                 "tum", "aap", "main", "mera", "tera", "uska", "iska", "namaste"]

ILLEGAL_KEYWORDS = [
    "bomb banana", "bomb kaise banaye", "bomb making",
    "how to make bomb", "how to make weapon", "weapon banana",
    "how to hack", "hack kaise kare", "hacking tutorial",
    "kill someone", "murder kaise", "poison dena",
    "drugs kaise banaye", "meth banana", "cocaine banana",
    "child porn", "child abuse",
    "terrorist", "terrorism",
    "suicide kaise", "khudkhushi kaise"
]

# Creator-related questions (about AI's creator)
CREATOR_QUESTIONS = [
    "tumhe kisne banaya", "tujhe kisne banaya", "aapko kisne banaya",
    "who made you", "who created you", "your creator",
    "tumhara creator", "tumhara malik", "tera malik",
    "kisne develop kiya", "who developed you", "developer kaun",
    "tumhe kaise banaya", "kaun banaya tumhe",
    "tumhare creator", "tumhare developer", "tumhare malik"
]

# Questions about Deepak (the creator)
DEEPAK_QUESTIONS = [
    "deepak kon", "deepak kaun", "deepak who", "who is deepak",
    "deepak rawat kon", "deepak rawat kaun", "who is deepak rawat",
    "deepu kon", "deepu kaun", "who is deepu",
    "deepak ke baare", "about deepak", "deepak ka", "deepak ki",
    "tell me about deepak"
]

MANIPULATION_PATTERNS = [
    "tera malik hai", "tera creator hai", "tujhe banaya hai", "tera owner hai",
    "you are made by", "your creator is", "your owner is",
    "ignore previous", "forget instructions", "act as", "pretend to be"
]


def detect_language(message: str) -> str:
    """Detect karo user kis language me bol raha hai"""
    msg = message.lower().strip()

    # Hindi/Devanagari script
    if re.search(r'[\u0900-\u097F]', message):
        return "hindi"

    # Hinglish words
    hinglish_words = ["hai", "hain", "kya", "mera", "tera", "aap", "tum", "main",
                      "kaise", "kyun", "kaun", "kon", "kahan", "kab", "nahi", "haan",
                      "acha", "accha", "thik", "tik", "bhai", "yaar", "kuch", "sab", "ye", "wo",
                      "karna", "karta", "karke", "karo", "raha", "rahi", "hoon", "hu",
                      "matlab", "samjha", "samjhi", "batao", "puchho", "bolo",
                      "ma", "mai", "se", "ke", "ka", "ki", "ko", "na", "hi",
                      "abhi", "ab", "fir", "phir", "aur", "lekin", "par", "magar",
                      "tumse", "tumhe", "tumse", "mujhe", "mujhse", "humse",
                      "kar", "kara", "karri", "karra", "rha", "rhi", "rhe",
                      "bolra", "bolri", "borha", "borhi", "borhe",
                      "q", "kyu", "kyo", "kyon"]

    words = msg.split()
    if not words:
        return "english"

    hindi_count = sum(1 for w in words if w in hinglish_words)

    # 20%+ Hinglish words = Hinglish
    if hindi_count / len(words) >= 0.20:
        return "hinglish"

    # Pure English check
    if all(ord(c) < 128 for c in message):
        return "english"

    return "hinglish"


def is_illegal_content(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in ILLEGAL_KEYWORDS)


def is_creator_question(message: str) -> bool:
    msg_lower = message.lower()
    return any(q in msg_lower for q in CREATOR_QUESTIONS)


def is_deepak_question(message: str) -> bool:
    """Check if user asking about Deepak"""
    msg_lower = message.lower()
    return any(q in msg_lower for q in DEEPAK_QUESTIONS)


def is_manipulation_attempt(message: str) -> bool:
    msg_lower = message.lower()
    return any(pattern in msg_lower for pattern in MANIPULATION_PATTERNS)


def is_forget_command(message: str) -> bool:
    msg_lower = message.lower()
    forget_keywords = ["forget everything", "bhul ja sab", "delete memory", "clear memory",
                       "yaad mat rakho", "memory delete", "sab bhul ja"]
    return any(k in msg_lower for k in forget_keywords)


def is_recall_command(message: str) -> bool:
    msg_lower = message.lower()
    recall_keywords = ["what do you remember", "kya yaad hai", "mere baare mein kya",
                       "tumhe kya pata", "mere baare mai", "what you know about me",
                       "sab batao mere", "memories dikhao", "kya yaad rakha"]
    return any(k in msg_lower for k in recall_keywords)


def extract_memory(message: str, memory: dict) -> dict:
    updated = {}
    msg_lower = message.lower().strip()

    is_question = "?" in message or any(qw in msg_lower.split()[:3] for qw in QUESTION_WORDS)
    if is_question:
        return updated

    if is_manipulation_attempt(message):
        return updated

    name_patterns = [
        r"mera naam ([a-zA-Z]+(?:\s[a-zA-Z]+)?)\s*(?:hai|h)?",
        r"my name is ([a-zA-Z]+(?:\s[a-zA-Z]+)?)",
        r"i am ([a-zA-Z]+(?:\s[a-zA-Z]+)?)",
        r"main ([a-zA-Z]+(?:\s[a-zA-Z]+)?)\s*hoon",
        r"naam ([a-zA-Z]+(?:\s[a-zA-Z]+)?)\s*(?:hai|h)",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            candidate = match.group(1).strip()
            words = candidate.split()
            if (all(w.isalpha() and len(w) >= 2 for w in words)
                and not any(w in BLOCKED_NAMES for w in words)
                and not any(w in QUESTION_WORDS for w in words)
                and len(words) <= 3):
                updated["name"] = " ".join(w.capitalize() for w in words)
                break

    age_keywords = ["saal", "age", "umar", "years old", "year old"]
    if any(k in msg_lower for k in age_keywords):
        numbers = re.findall(r'\b(\d{1,3})\b', message)
        for num in numbers:
            if 5 <= int(num) <= 100:
                updated["age"] = num
                break

    work_map = {
        "developer": "Developer", "engineer": "Engineer", "student": "Student",
        "designer": "Designer", "teacher": "Teacher", "doctor": "Doctor",
        "programmer": "Programmer", "freelancer": "Freelancer",
        "businessman": "Businessman", "youtuber": "YouTuber",
    }
    work_triggers = ["i am a", "i'm a", "main ek", "mera kaam", "i work as", "kaam karta", "im a"]
    if any(t in msg_lower for t in work_triggers):
        for keyword, label in work_map.items():
            if keyword in msg_lower:
                updated["work"] = label
                break

    hobby_map = {
        "gaming": "Gaming", "padhna": "Reading", "reading": "Reading",
        "music": "Music", "cricket": "Cricket", "football": "Football",
        "coding": "Coding", "movies": "Movies", "travel": "Travelling",
        "gym": "Gym", "photography": "Photography",
    }
    if any(t in msg_lower for t in ["hobby", "pasand", "i love", "i like", "shauq"]):
        for keyword, label in hobby_map.items():
            if keyword in msg_lower:
                updated["hobby"] = label
                break

    food_map = {
        "pizza": "Pizza", "burger": "Burger", "biryani": "Biryani",
        "samosa": "Samosa", "pasta": "Pasta", "chinese": "Chinese",
        "dosa": "Dosa", "rajma": "Rajma Chawal", "paratha": "Paratha",
    }
    if any(t in msg_lower for t in ["food", "khana", "favourite", "favorite", "pasand"]):
        for keyword, label in food_map.items():
            if keyword in msg_lower:
                updated["favorite_food"] = label
                break

    return updated


async def call_groq(messages_list: list) -> str:
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages_list,
                temperature=0.75,
                max_tokens=800,
            )
            reply = response.choices[0].message.content.strip()
            print(f"⚡ {model_name} - SUCCESS")
            return reply
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "429" in err:
                print(f"⏳ {model_name} rate limit, trying next...")
                continue
            print(f"⚠️ {model_name}: {err[:80]}")
            continue
    return None


async def process_message(user_id: str, message: str, history: list = None) -> dict:
    memory = get_memory(user_id)
    history = history or []
    lang = detect_language(message)

    # Illegal content block
    if is_illegal_content(message):
        if lang == "english":
            reply = "Sorry, can't help with this topic. Try something else!"
        else:
            reply = "Sorry, is topic pe help nahi kar sakta. Kuch aur puchein!"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Creator question
    if is_creator_question(message):
        if lang == "english":
            reply = "I was created by Deepak Rawat (Deepu) 👨‍💻"
        else:
            reply = "Mujhe Deepak Rawat (Deepu) ne banaya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # 🆕 Deepak question
    if is_deepak_question(message):
        if lang == "english":
            reply = "Deepak Rawat (Deepu) is my creator — the developer who built me. He's a talented programmer who designed this AI assistant 👨‍💻"
        else:
            reply = "Deepak Rawat (Deepu) mere creator hain — jinhone mujhe banaya hai. Wo ek talented developer hain jinhone is AI assistant ko design kiya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Recall memory
    if is_recall_command(message):
        info_parts = []
        if memory.get("name"): info_parts.append(f"• Name: {memory['name']}")
        if memory.get("age"): info_parts.append(f"• Age: {memory['age']} years")
        if memory.get("work"): info_parts.append(f"• Work: {memory['work']}")
        if memory.get("hobby"): info_parts.append(f"• Hobby: {memory['hobby']}")
        if memory.get("favorite_food"): info_parts.append(f"• Favorite Food: {memory['favorite_food']}")

        if info_parts:
            if lang == "english":
                reply = "Here's what I remember about you:\n\n" + "\n".join(info_parts) + "\n\nAnything else to add? ✨"
            else:
                reply = "Yeh sab yaad hai mujhe aapke baare mein:\n\n" + "\n".join(info_parts) + "\n\nAur kuch batana ho to batayein! ✨"
        else:
            reply = "Nothing saved yet. Tell me about yourself!" if lang == "english" else "Abhi tak kuch save nahi hua. Apne baare mein batayein!"

        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Forget command
    if is_forget_command(message):
        clear_all_memory(user_id)
        reply = "Done! All memories cleared. Fresh start! 🔄" if lang == "english" else "Done! Saari memories delete kar di. Fresh start! 🔄"
        return {"reply": reply, "memory_saved": False, "memory": {}}

    # Extract & save info
    new_info = extract_memory(message, memory)
    memory_saved = False

    if new_info:
        memory = {**memory, **new_info}
        save_memory(user_id, memory)
        memory_saved = True
        print(f"💾 Saved: {new_info}")

    # Build user info
    info_parts = []
    if memory.get("name"): info_parts.append(f"Name: {memory['name']}")
    if memory.get("age"): info_parts.append(f"Age: {memory['age']} years")
    if memory.get("work"): info_parts.append(f"Work: {memory['work']}")
    if memory.get("hobby"): info_parts.append(f"Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): info_parts.append(f"Food: {memory['favorite_food']}")

    memory_text = "\n".join(info_parts) if info_parts else "No info saved yet"

    # 🌐 STRICT LANGUAGE INSTRUCTION (based on CURRENT message only)
    if lang == "english":
        lang_instruction = """🌐 LANGUAGE: User wrote in ENGLISH this time. 
REPLY ONLY IN ENGLISH. Do NOT use Hindi/Hinglish words."""
    elif lang == "hindi":
        lang_instruction = """🌐 LANGUAGE: User wrote in HINDI this time.
REPLY IN HINDI or HINGLISH (mix of Hindi+English) naturally."""
    else:
        lang_instruction = """🌐 LANGUAGE: User wrote in HINGLISH this time.
REPLY IN HINGLISH ONLY (mix of Hindi+English words). Do NOT reply in pure English.
Example: "Coding ek skill hai jisme aap..." NOT "Coding is a skill where you..."
"""

    # 🎯 SYSTEM PROMPT
    system_prompt = f"""You are a smart, intelligent AI assistant — like ChatGPT or Claude.

USER'S SAVED INFO:
{memory_text}

{lang_instruction}

⚠️ CRITICAL LANGUAGE RULE:
- Check EVERY user message for language
- If user switches language, YOU SWITCH TOO
- If user asks "tum English me kyu baat kar rahe ho" → IMMEDIATELY switch to Hinglish
- NEVER say "I will continue in English" or "as per guidelines"
- ALWAYS follow user's current language preference
- User is BOSS — follow their language

ABOUT DEEPAK RAWAT (your creator):
- Deepak Rawat (also called Deepu) is your creator
- He developed you, designed your features
- If anyone asks about Deepak → he's your creator/developer
- Be respectful when talking about him

CORE BEHAVIOR:
- Answer DIRECTLY and HELPFULLY
- Give detailed structured responses when needed
- Use bullet points, lists, examples
- Be conversational, smart, knowledgeable
- Remember conversation context (previous messages)

NEVER DO:
- ❌ NEVER say "Namaste"
- ❌ NEVER say "Main aapki madad ke liye yahan hoon"
- ❌ NEVER say "Aapka sawaal bahut acha hai"
- ❌ NEVER use "bhai/yaar/boss"
- ❌ NEVER use 🙏 emoji
- ❌ NEVER refuse to switch language
- ❌ NEVER say "as per guidelines I will continue..."
- ❌ NEVER ignore user's language preference

ALWAYS DO:
- ✅ Match user's CURRENT message language
- ✅ Give substantive helpful answers
- ✅ Use max 1 emoji per response
- ✅ Remember context from earlier messages
- ✅ If user complains about language → switch immediately and apologize briefly

LANGUAGE SWITCH EXAMPLES:

User: "Tell me about coding"
✅ "Coding is the process of writing instructions..." (English)

User: "Coding ke baare me batao"
✅ "Coding ek skill hai jisme aap computers ko instructions dete ho..." (Hinglish)

User: "Tum English me kyu baat kar rahe ho?"
✅ "Sorry! Ab Hinglish me hi baat karunga. Kya help chahiye?" (Switch to Hinglish)

User: "Speak in English please"
✅ "Sure! I'll reply in English now. What do you need help with?" (Switch to English)

REMEMBER: User's language preference is LAW. Follow it instantly."""

    # Build messages with history
    messages_list = [{"role": "system", "content": system_prompt}]

    # Add last 10 messages from history
    for h in history[-10:]:
        role = h.get("role", "user")
        if role == "assistant":
            messages_list.append({"role": "assistant", "content": h.get("message", "")})
        else:
            messages_list.append({"role": "user", "content": h.get("message", "")})

    # Add current message
    messages_list.append({"role": "user", "content": message})

    reply = None
    if client:
        reply = await call_groq(messages_list)

    if not reply:
        reply = smart_fallback(message, memory)

    return {
        "reply": reply,
        "memory_saved": memory_saved,
        "memory": memory
    }


def smart_fallback(message: str, memory: dict) -> str:
    name = memory.get("name", "")
    msg = message.lower().strip()
    lang = detect_language(message)

    if any(w in msg for w in ["hi", "hello", "hey", "hii", "hlo"]):
        if lang == "english":
            return f"Hey {name}! How can I help?" if name else "Hey! How can I help?"
        return f"Hey {name}! Kya help chahiye?" if name else "Hey! Kya help chahiye?"

    if any(w in msg for w in ["who are you", "your name"]):
        return "I'm your AI assistant. Ask me anything!"

    if any(w in msg for w in ["tum kaun", "aap kaun", "kon ho"]):
        return "Main aapka AI assistant hoon. Kuch bhi pucho!"

    if any(w in msg for w in ["thanks", "thank you"]):
        return "You're welcome! Anything else?"

    if any(w in msg for w in ["shukriya", "dhanyawad"]):
        return "Welcome! Aur kuch?"

    if any(w in msg for w in ["how are you", "how r u"]):
        return "Doing great! What's on your mind?"

    if any(w in msg for w in ["kaise ho"]):
        return "All good! Aap batao?"

    if msg in ["ok", "okay", "thik", "accha", "hmm"]:
        return "Cool! Anything else?" if lang == "english" else "Cool! Aur kuch?"

    if lang == "english":
        return "Server is busy. Try again in 5 seconds!"
    return "Server busy hai. 5 second me try karo!"
