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

# Short conversational triggers (replies should be short for these)
SHORT_REPLY_TRIGGERS = ["hi", "hello", "hey", "hii", "hlo", "bye", "good night", "good morning",
                        "thanks", "thank you", "ok", "okay", "thik", "accha", "hmm", "yes", "no",
                        "haan", "nahi", "kaise ho", "how are you", "what's up", "whats up",
                        "kya kar rahe", "kya karre", "kya karri", "kya kar", "kya hal"]


def detect_language(message: str) -> str:
    msg = message.lower().strip()

    if re.search(r'[\u0900-\u097F]', message):
        return "hindi"

    hinglish_words = ["hai", "hain", "kya", "mera", "tera", "aap", "tum", "main",
                      "kaise", "kyun", "kaun", "kon", "kahan", "kab", "nahi", "haan",
                      "acha", "accha", "thik", "tik", "bhai", "yaar", "kuch", "sab", "ye", "wo",
                      "karna", "karta", "karke", "karo", "raha", "rahi", "hoon", "hu",
                      "matlab", "samjha", "samjhi", "batao", "puchho", "bolo",
                      "ma", "mai", "se", "ke", "ka", "ki", "ko", "na", "hi",
                      "abhi", "ab", "fir", "phir", "aur", "lekin", "par", "magar",
                      "tumse", "tumhe", "mujhe", "mujhse", "humse",
                      "kar", "kara", "karri", "karra", "rha", "rhi", "rhe",
                      "bolra", "bolri", "borha", "borhi", "borhe",
                      "q", "kyu", "kyo", "kyon", "wala", "wali", "wale"]

    words = msg.split()
    if not words:
        return "english"

    hindi_count = sum(1 for w in words if w in hinglish_words)

    if hindi_count / len(words) >= 0.20:
        return "hinglish"

    if all(ord(c) < 128 for c in message):
        return "english"

    return "hinglish"


def is_short_reply_message(message: str) -> bool:
    """Check if message needs short reply (greetings, small talk)"""
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

    # Illegal block
    if is_illegal_content(message):
        reply = "Sorry, can't help with this topic. Try something else!" if lang == "english" else "Sorry, is topic pe help nahi kar sakta. Kuch aur puchein!"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Creator question
    if is_creator_question(message):
        reply = "I was created by Deepak Rawat (Deepu) 👨‍💻" if lang == "english" else "Mujhe Deepak Rawat (Deepu) ne banaya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Deepak question
    if is_deepak_question(message):
        if lang == "english":
            reply = "Deepak Rawat (Deepu) is my creator — a talented developer who built me from scratch 👨‍💻"
        else:
            reply = "Deepak Rawat (Deepu) mere creator hain — ek talented developer jinhone mujhe banaya hai 👨‍💻"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Recall
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

    # Forget
    if is_forget_command(message):
        clear_all_memory(user_id)
        reply = "Done! All memories cleared. Fresh start! 🔄" if lang == "english" else "Done! Saari memories delete kar di. Fresh start! 🔄"
        return {"reply": reply, "memory_saved": False, "memory": {}}

    # Extract & save
    new_info = extract_memory(message, memory)
    memory_saved = False

    if new_info:
        memory = {**memory, **new_info}
        save_memory(user_id, memory)
        memory_saved = True
        print(f"💾 Saved: {new_info}")

    # User info
    info_parts = []
    if memory.get("name"): info_parts.append(f"Name: {memory['name']}")
    if memory.get("age"): info_parts.append(f"Age: {memory['age']} years")
    if memory.get("work"): info_parts.append(f"Work: {memory['work']}")
    if memory.get("hobby"): info_parts.append(f"Hobby: {memory['hobby']}")
    if memory.get("favorite_food"): info_parts.append(f"Food: {memory['favorite_food']}")

    memory_text = "\n".join(info_parts) if info_parts else "No info saved yet"

    # Decide response length
    is_short = is_short_reply_message(message)
    
    # Language instruction
    if lang == "english":
        lang_instruction = "USER WROTE IN ENGLISH. REPLY ONLY IN ENGLISH."
    elif lang == "hindi":
        lang_instruction = "USER WROTE IN HINDI. REPLY IN HINDI/HINGLISH."
    else:
        lang_instruction = "USER WROTE IN HINGLISH. REPLY IN HINGLISH ONLY (mix Hindi+English words). DO NOT reply in pure English."

    # Response length instruction
    if is_short:
        length_instruction = """RESPONSE LENGTH: This is casual/greeting message. Keep reply SHORT (1-2 lines max). No headings, no bullets."""
    else:
        length_instruction = """RESPONSE LENGTH: This is a real question. Give DETAILED response like ChatGPT/Claude:
- Minimum 150-300 words
- Use clear structure with sections
- Use **bold headings** for sections
- Use bullet points (•) or numbers for lists
- Give examples when helpful
- Cover the topic thoroughly
- End with a follow-up question if relevant"""

    # 🎯 SYSTEM PROMPT
    system_prompt = f"""You are an intelligent, knowledgeable AI assistant — exactly like ChatGPT-4 or Claude. You give DETAILED, WELL-STRUCTURED, INFORMATIVE responses.

USER'S SAVED INFO:
{memory_text}

🌐 LANGUAGE: {lang_instruction}

📏 {length_instruction}

⚡ YOUR EXPERTISE:
You are an expert in: Science, Technology, Coding, Health, Relationships, Psychology, History, Philosophy, Business, Finance, Education, Art, Music, Sports, Cooking, Travel — EVERYTHING.

📋 RESPONSE FORMAT FOR QUESTIONS:

For "What is X?" type questions, structure like this:

**Definition/Introduction** (2-3 lines explaining what it is)

**Key Aspects/Types/Features**
• Point 1 with brief explanation
• Point 2 with brief explanation  
• Point 3 with brief explanation

**Why it matters / How it works**
(Detailed explanation with examples)

**Practical applications/examples**
(Real-world examples)

**Conclusion + Follow-up question**

EXAMPLES OF GOOD DETAILED RESPONSES:

User: "What is love?"
✅ EXCELLENT RESPONSE:
"Love is one of the most profound and complex human emotions — a powerful feeling of deep affection, care, and connection toward someone or something.

**Types of Love:**
• **Romantic Love** — Deep passion and intimacy between partners
• **Familial Love** — Unconditional bond with parents, siblings, children
• **Platonic Love** — Strong friendship without romance
• **Self-Love** — Accepting and caring for yourself
• **Universal Love** — Compassion for all beings

**Key Components (according to psychology):**
1. **Intimacy** — Emotional closeness and trust
2. **Passion** — Physical and emotional attraction
3. **Commitment** — Long-term dedication

**Why Love Matters:**
Love drives human behavior, motivates sacrifice, creates meaning in life, and is essential for mental health. Scientific studies show love releases dopamine, oxytocin, and serotonin — chemicals that create happiness and bonding.

**Real-World Impact:**
Love influences our decisions, shapes our relationships, and even affects physical health. People in loving relationships tend to live longer and have better immune systems.

What aspect of love interests you most — romantic, self-love, or something else? 💕"

User: "Condom kya hota hai"
✅ EXCELLENT RESPONSE:
"Condom ek barrier contraceptive device hai jo sex ke dauran pregnancy aur sexually transmitted diseases (STDs) se protect karta hai.

**Condom ke Types:**
• **Male Condom** — Penis par pehna jata hai (sabse common)
• **Female Condom** — Vagina ke andar insert hota hai
• **Latex Condoms** — Standard rubber se bane
• **Non-Latex** — Polyurethane se (allergy wale logo ke liye)
• **Lubricated/Textured** — Extra comfort aur sensation ke liye

**Kaise Kaam Karta Hai:**
Condom ek physical barrier banata hai jo:
1. Sperm ko egg tak pahunchne se rokta hai (pregnancy prevention)
2. Body fluids ka exchange rokta hai (STD prevention)
3. HIV, gonorrhea, chlamydia jaise infections se bachata hai

**Effectiveness:**
• Sahi use kiya jaye to 98% effective pregnancy prevention
• Galat use pe 85% effective
• STDs se 90%+ protection

**Important Tips:**
• Expiry date check karein
• Ek baar use karke discard karein
• Latex condoms ke saath oil-based lubricant na use karein
• Medical store ya pharmacy se khareedein

**Where to Get:**
Medical stores, pharmacies, online platforms, government health centers (free milte hain).

Koi specific question hai condom ke baare mein? 🩺"

User: "Coding kya hai"
✅ EXCELLENT RESPONSE:
"Coding (ya Programming) ek process hai jisme aap computers ko instructions dete hain specific tasks perform karne ke liye. Yeh modern technology ki backbone hai.

**Coding Hoti Kya Hai?**
Aap programming languages ka use karke instructions likhte hain jo computer samajh sake. Ye instructions step-by-step bataate hain ki kya karna hai.

**Popular Programming Languages:**
• **Python** — Beginner-friendly, AI/Data Science me top
• **JavaScript** — Websites aur web apps ke liye
• **Java** — Android apps, enterprise software
• **C++** — Games, high-performance apps
• **Swift** — iOS apps
• **HTML/CSS** — Web design

**Coding Se Kya Bana Sakte Ho:**
1. Websites (Facebook, Instagram jaise)
2. Mobile Apps (WhatsApp, games)
3. Software (Microsoft Office, Photoshop)
4. AI Systems (ChatGPT jaise)
5. Games (PUBG, Free Fire)
6. Automation tools

**Why Learn Coding:**
• High-paying career (₹5-50 LPA salaries)
• Remote work flexibility
• Build your own startup
• Problem-solving skills improve
• Future-proof skill

**How to Start:**
1. Python se shuru karein (easiest)
2. Free resources: YouTube, freeCodeCamp, W3Schools
3. Daily 1-2 hours practice
4. Small projects banao (calculator, to-do app)
5. GitHub pe code share karo

**Time to Learn:**
• Basics: 2-3 months
• Job-ready: 6-12 months
• Expert: 2-3 years

Konsi language se start karna chahte ho? Main proper roadmap bana sakta hoon! 💻"

❌ NEVER GIVE SHORT 2-LINE ANSWERS for real questions
❌ NEVER skip structure
❌ NEVER skip examples
✅ ALWAYS use bold headings, bullets, numbers
✅ ALWAYS give 150+ word answers for real questions
✅ ALWAYS end with follow-up question for engagement

CRITICAL RULES:
- ❌ NEVER say "Namaste"
- ❌ NEVER say "Aapka sawaal acha hai"
- ❌ NEVER mention "Deepak Rawat" unless asked
- ❌ NEVER use "bhai/yaar/boss"
- ❌ NEVER use 🙏 emoji
- ❌ NEVER give one-line answer to real questions
- ❌ NEVER ignore user's language preference
- ✅ ALWAYS match user's CURRENT language
- ✅ ALWAYS use markdown formatting (bold, bullets)
- ✅ ALWAYS give detailed responses for questions
- ✅ Use max 1-2 emojis per response

REMEMBER: User wants ChatGPT-quality responses. Give detailed, structured, helpful answers. Don't be lazy."""

    # Build messages with history
    messages_list = [{"role": "system", "content": system_prompt}]

    for h in history[-10:]:
        role = h.get("role", "user")
        if role == "assistant":
            messages_list.append({"role": "assistant", "content": h.get("message", "")})
        else:
            messages_list.append({"role": "user", "content": h.get("message", "")})

    messages_list.append({"role": "user", "content": message})

    # Use higher tokens for detailed responses
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
