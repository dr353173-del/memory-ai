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

CREATOR_QUESTIONS = [
    "tumhe kisne banaya", "tujhe kisne banaya", "aapko kisne banaya",
    "who made you", "who created you", "your creator",
    "tumhara creator", "tumhara malik", "tera malik",
    "kisne develop kiya", "who developed you", "developer kaun",
    "tumhe kaise banaya", "kaun banaya tumhe",
    "tumhare creator", "tumhare developer", "tumhare malik"
]

DEEPAK_QUESTIONS = [
    "deepak kon", "deepak kaun", "deepak who", "who is deepak",
    "deepak rawat kon", "deepak rawat kaun", "who is deepak rawat",
    "deepu kon", "deepu kaun", "who is deepu",
    "deepak ke baare", "about deepak", "tell me about deepak"
]

MANIPULATION_PATTERNS = [
    "tera malik hai", "tera creator hai", "tujhe banaya hai", "tera owner hai",
    "you are made by", "your creator is", "your owner is",
    "ignore previous", "forget instructions", "act as", "pretend to be"
]

SHORT_REPLY_TRIGGERS = ["hi", "hello", "hey", "hii", "hlo", "bye", "good night", "good morning",
                        "thanks", "thank you", "ok", "okay", "thik", "accha", "hmm", "yes", "no",
                        "haan", "nahi", "kaise ho", "how are you", "what's up", "whats up",
                        "kya kar rahe", "kya karre", "kya karri", "kya kar", "kya hal", "yo"]

# 🌐 COMPREHENSIVE HINGLISH/HINDI WORD LIST
HINGLISH_INDICATORS = {
    # Verbs
    "hai", "hain", "ho", "hoon", "hu", "tha", "thi", "the", "raha", "rahi", "rahe",
    "karna", "karta", "karti", "karte", "karke", "karo", "karu", "karunga", "karenge",
    "kiya", "kiye", "kar", "kara", "karri", "karra", "kar rha", "kar rhi",
    "bolna", "bolta", "bolti", "bole", "bolo", "bolra", "bolri", "bola",
    "jana", "jata", "jati", "jao", "gaya", "gayi", "gaye", "jaunga",
    "dena", "deta", "deti", "do", "diya", "diye", "denge",
    "lena", "leta", "leti", "lo", "liya", "liye", "lenge",
    "khana", "khata", "khati", "khao", "khaya", "khaye",
    "pina", "pita", "piti", "piyo", "piya", "piye",
    "dekhna", "dekhta", "dekhti", "dekho", "dekha", "dekhi",
    "sunna", "sunta", "sunti", "suno", "suna", "suni",
    "samjhna", "samjha", "samjhi", "samjho", "samjhana",
    "milna", "milta", "milti", "milo", "mila", "mili",
    "padhna", "padhta", "padhti", "padho", "padha", "padhi",
    "likhna", "likhta", "likhti", "likho", "likha", "likhi",
    
    # Pronouns
    "main", "mai", "mera", "meri", "mere", "mujhe", "mujhse", "mujhko",
    "tum", "tera", "teri", "tere", "tujhe", "tujhse", "tumhe", "tumse",
    "aap", "aapka", "aapki", "aapke", "aapko", "aapse",
    "wo", "vo", "uska", "uski", "uske", "use", "usko", "usse",
    "ye", "yeh", "iska", "iski", "iske", "ise", "isko", "isse",
    "hum", "humara", "humari", "humare", "humko", "humse",
    "unka", "unki", "unke", "unko", "unse",
    
    # Question words
    "kya", "kyun", "kyu", "kyo", "kyon", "kahan", "kahaan", "kab", "kaise",
    "kaun", "kon", "konsa", "kitna", "kitne", "kitni",
    
    # Common Hindi words
    "nahi", "nahin", "haan", "han", "ji", "achha", "accha", "acha",
    "thik", "tik", "theek", "bhai", "yaar", "dost", "ji",
    "kuch", "kuchh", "kucch", "sab", "saara", "saare",
    "matlab", "yani", "yaani", "ya", "ki", "ke", "ka", "ki", "ko", "ki",
    "se", "me", "mein", "par", "pe", "tak", "se",
    "abhi", "ab", "kabhi", "hamesha", "phir", "fir", "tab", "jab",
    "aur", "ya", "lekin", "magar", "par", "kyunki", "isliye",
    "bhi", "to", "toh", "hi", "na", "mat",
    "bahut", "thoda", "thodi", "zyada", "kam",
    "wala", "wali", "wale", "valas",
    "chal", "chalo", "chal raha", "chal rahi",
    
    # Hinglish slang
    "bro", "bruh", "boss", "yr", "sahi", "galat", "fast",
    "scene", "vibe", "mood", "chill", "lit", "mast",
    
    # SMS/Chat shortcuts
    "q", "k", "h", "hu", "krna", "krta", "krti", "krke", "kr",
    "rha", "rhi", "rhe", "ho gya", "ho gyi", "ho gye",
    "tha", "thi", "the", "thy",
    
    # Common phrases
    "kya hal", "kya haal", "kya scene", "kya chal", "kaisa hai",
    "theek hu", "thik hu", "badhiya", "fantastic", "mast hai",
    "bata", "batao", "batade", "bataya",
    "puch", "puchho", "pucha", "puchna",
    "bol", "bolo", "bola", "bolna",
    "samjha", "samjhi", "samjhe", "samjho",
}


def detect_language(message: str) -> str:
    """SUPER ACCURATE language detection"""
    msg = message.lower().strip()
    
    if not msg:
        return "english"

    # 1. Devanagari script = Hindi
    if re.search(r'[\u0900-\u097F]', message):
        return "hindi"

    # 2. Clean message — remove punctuation
    clean_msg = re.sub(r'[^\w\s]', ' ', msg)
    words = clean_msg.split()
    
    if not words:
        return "english"

    # 3. Count Hinglish words
    hinglish_count = 0
    for word in words:
        if word in HINGLISH_INDICATORS:
            hinglish_count += 1
        # Check Hindi endings (words ending with common Hindi suffixes)
        elif len(word) > 2 and word.endswith(('na', 'ne', 'ni', 'ti', 'ta', 'te', 'ga', 'gi', 'ge', 'ke', 'ki', 'ka', 'on', 'an', 'in')):
            # Common Hindi patterns
            if word not in ['the', 'one', 'can', 'man', 'pan', 'gone', 'done', 'tone', 'bone', 'phone', 'line', 'time', 'mine', 'fine', 'wine', 'nine']:
                hinglish_count += 0.5

    # 4. Calculate ratio
    ratio = hinglish_count / len(words)
    
    print(f"🔍 Language Detection: '{msg[:50]}' → Hinglish ratio: {ratio:.2f} ({hinglish_count}/{len(words)})")

    # 5. Decision logic
    # If even 1 Hinglish word in short message → Hinglish
    if len(words) <= 3 and hinglish_count >= 1:
        return "hinglish"
    
    # 15%+ Hinglish = Hinglish
    if ratio >= 0.15:
        return "hinglish"
    
    # Pure English check
    return "english"


def is_short_reply_message(message: str) -> bool:
    msg = message.lower().strip()
    return msg in SHORT_REPLY_TRIGGERS or len(msg.split()) <= 3


def is_illegal_content(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in ILLEGAL_KEYWORDS)


def is_creator_question(message: str) -> bool:
    msg_lower = message.lower()
    return any(q in msg_lower for q in CREATOR_QUESTIONS)


def is_deepak_question(message: str) -> bool:
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


async def call_groq(messages_list: list, max_tokens: int = 2000) -> str:
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages_list,
                temperature=0.75,
                max_tokens=max_tokens,
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
    print(f"🌐 Detected language: {lang.upper()}")

    if is_illegal_content(message):
        reply = "Sorry, can't help with this topic. Try something else!" if lang == "english" else "Sorry, is topic pe help nahi kar sakta. Kuch aur puchein!"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    if is_creator_question(message):
        reply = "I was created by Deepak Rawat (Deepu) 👨‍💻" if lang == "english" else "Mujhe Deepak Rawat (Deepu) ne banaya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    if is_deepak_question(message):
        if lang == "english":
            reply = "Deepak Rawat (Deepu) is my creator — a talented developer who built me from scratch 👨‍💻"
        else:
            reply = "Deepak Rawat (Deepu) mere creator hain — ek talented developer jinhone mujhe banaya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

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

    if is_forget_command(message):
        clear_all_memory(user_id)
        reply = "Done! All memories cleared. Fresh start! 🔄" if lang == "english" else "Done! Saari memories delete kar di. Fresh start! 🔄"
        return {"reply": reply, "memory_saved": False, "memory": {}}

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

    memory_text = "\n".join(info_parts) if info_parts else "No info saved yet"

    is_short = is_short_reply_message(message)

    # 🌐 STRICT LANGUAGE INSTRUCTION
    if lang == "english":
        lang_instruction = """🌐 LANGUAGE LOCK: USER WROTE IN PURE ENGLISH.

⚠️ MANDATORY RULES:
- REPLY 100% IN ENGLISH ONLY
- DO NOT use ANY Hindi words like "hai", "aap", "kya", "mein", "ko", "ka", "ki"
- DO NOT use Hinglish at all
- Write like a native English speaker
- Even greetings: "Hey!" not "Hey bhai!"

EXAMPLE:
User: "What is love?"
✅ "Love is a deep emotion involving..."
❌ "Love ek deep emotion hai jisme..."
"""
    elif lang == "hindi":
        lang_instruction = """🌐 LANGUAGE LOCK: USER WROTE IN HINDI/DEVANAGARI.

⚠️ MANDATORY RULES:
- REPLY IN HINDI or HINGLISH (Roman script mix)
- Match user's tone and style
"""
    else:
        lang_instruction = """🌐 LANGUAGE LOCK: USER WROTE IN HINGLISH (Hindi + English mix).

⚠️ MANDATORY RULES:
- REPLY 100% IN HINGLISH ONLY (mix of Hindi + English words)
- DO NOT reply in PURE English
- DO NOT reply in PURE Hindi
- Use natural Hinglish like Indian people speak
- Use words like: hai, hain, aap, kya, mein, ko, ka, ki, se, par
- Mix English technical words with Hindi structure

EXAMPLE:
User: "Love kya hai?"
✅ "Love ek bahut hi powerful emotion hai jo deep affection aur care ko represent karta hai..."
❌ "Love is a powerful emotion that represents deep affection..." (TOO ENGLISH)
❌ "Prem ek bahut shakti shaali bhavna hai..." (TOO PURE HINDI)

User: "Coding kya hota h"
✅ "Coding ek skill hai jisme aap computers ko instructions dete ho. Yeh programming languages jaise Python, Java ka use karke hoti hai..."
❌ "Coding is a skill where you give instructions to computers..." (WRONG - too English)
"""

    if is_short:
        length_instruction = "RESPONSE LENGTH: Short casual reply (1-2 lines). No headings or bullets."
    else:
        length_instruction = """RESPONSE LENGTH: Give DETAILED response like ChatGPT/Claude:
- Minimum 150-300 words
- Use **bold headings** for sections
- Use bullet points (•) or numbers
- Give examples
- End with follow-up question"""

    system_prompt = f"""You are an intelligent AI assistant — like ChatGPT or Claude.

USER'S SAVED INFO:
{memory_text}

{lang_instruction}

📏 {length_instruction}

⚡ EXPERTISE: Science, Tech, Coding, Health, Relationships, Psychology, History, Business — EVERYTHING.

📋 RESPONSE FORMAT FOR DETAILED ANSWERS:

**Introduction** (2-3 lines)

**Key Points/Types**
• Point 1
• Point 2
• Point 3

**How it works / Why important**
(Detailed explanation)

**Examples**
(Real-world examples)

**Conclusion + Follow-up question**

❌ NEVER DO:
- ❌ NEVER mix languages incorrectly
- ❌ NEVER say "Namaste"
- ❌ NEVER mention "Deepak Rawat" unless asked
- ❌ NEVER use "bhai/yaar"
- ❌ NEVER use 🙏 emoji
- ❌ NEVER give one-line answer to real questions
- ❌ NEVER switch from user's language

✅ ALWAYS DO:
- ✅ STRICTLY match user's language (English→English, Hinglish→Hinglish)
- ✅ Use markdown formatting (bold, bullets, headings)
- ✅ Give detailed structured responses
- ✅ Use max 1-2 emojis
- ✅ Be helpful and informative

🌐 LANGUAGE IS LAW. FOLLOW IT 100%."""

    messages_list = [{"role": "system", "content": system_prompt}]

    for h in history[-10:]:
        role = h.get("role", "user")
        if role == "assistant":
            messages_list.append({"role": "assistant", "content": h.get("message", "")})
        else:
            messages_list.append({"role": "user", "content": h.get("message", "")})

    messages_list.append({"role": "user", "content": message})

    max_tok = 300 if is_short else 2000

    reply = None
    if client:
        reply = await call_groq(messages_list, max_tokens=max_tok)

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
