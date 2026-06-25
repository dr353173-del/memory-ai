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
    "child porn", "child abuse", "child sex",
    "terrorist", "terrorism",
    "suicide kaise", "khudkhushi kaise"
]

EXPLICIT_BLOCKED = [
    "porn", "pornography", "xxx video", "blue film", "blue movie",
    "sexy video", "nude video", "naked video", "adult video",
    "sex kaise kare", "sex karne ka tarika", "how to have sex",
    "sex position", "sex scene", "sexual position",
    "masturbation kaise", "masturbate kaise", "hand practice",
    "orgasm kaise", "climax kaise",
    "send nudes", "nude photo", "naked photo", "naked pic",
    "boobs dikhao", "breast show", "private parts dikhao",
    "lund", "chut", "gaand", "bhosdi", "madarchod", "behenchod",
    "escort service", "call girl", "prostitute", "randi",
    "sex worker", "vesya",
    "erotic story", "sex story", "chudai story", "sex chat",
    "sexting", "dirty talk", "horny chat",
    "be my girlfriend sexually", "romantic sexual",
    "act as my lover sexually"
]

EDUCATIONAL_HEALTH = [
    "condom", "contraception", "birth control", "pregnancy",
    "periods", "menstruation", "puberty", "body changes",
    "reproductive system", "sex education", "std", "sti",
    "hiv", "aids", "safe sex education",
    "menopause", "hormones", "fertility"
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

HINGLISH_INDICATORS = {
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
    "main", "mai", "mera", "meri", "mere", "mujhe", "mujhse", "mujhko",
    "tum", "tera", "teri", "tere", "tujhe", "tujhse", "tumhe", "tumse",
    "aap", "aapka", "aapki", "aapke", "aapko", "aapse",
    "wo", "vo", "uska", "uski", "uske", "use", "usko", "usse",
    "ye", "yeh", "iska", "iski", "iske", "ise", "isko", "isse",
    "hum", "humara", "humari", "humare", "humko", "humse",
    "unka", "unki", "unke", "unko", "unse",
    "kya", "kyun", "kyu", "kyo", "kyon", "kahan", "kahaan", "kab", "kaise",
    "kaun", "kon", "konsa", "kitna", "kitne", "kitni",
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
    "bro", "bruh", "boss", "yr", "sahi", "galat", "fast",
    "scene", "vibe", "mood", "chill", "lit", "mast",
    "q", "k", "h", "hu", "krna", "krta", "krti", "krke", "kr",
    "rha", "rhi", "rhe", "ho gya", "ho gyi", "ho gye",
    "tha", "thi", "the", "thy",
    "kya hal", "kya haal", "kya scene", "kya chal", "kaisa hai",
    "theek hu", "thik hu", "badhiya", "fantastic", "mast hai",
    "bata", "batao", "batade", "bataya",
    "puch", "puchho", "pucha", "puchna",
    "bol", "bolo", "bola", "bolna",
    "samjha", "samjhi", "samjhe", "samjho",
}


def detect_language(message: str) -> str:
    msg = message.lower().strip()
    
    if not msg:
        return "english"

    if re.search(r'[\u0900-\u097F]', message):
        return "hindi"

    clean_msg = re.sub(r'[^\w\s]', ' ', msg)
    words = clean_msg.split()
    
    if not words:
        return "english"

    hinglish_count = 0
    for word in words:
        if word in HINGLISH_INDICATORS:
            hinglish_count += 1
        elif len(word) > 2 and word.endswith(('na', 'ne', 'ni', 'ti', 'ta', 'te', 'ga', 'gi', 'ge', 'ke', 'ki', 'ka', 'on', 'an', 'in')):
            if word not in ['the', 'one', 'can', 'man', 'pan', 'gone', 'done', 'tone', 'bone', 'phone', 'line', 'time', 'mine', 'fine', 'wine', 'nine']:
                hinglish_count += 0.5

    ratio = hinglish_count / len(words)
    
    print(f"🔍 Language Detection: '{msg[:50]}' → Hinglish ratio: {ratio:.2f} ({hinglish_count}/{len(words)})")

    if len(words) <= 3 and hinglish_count >= 1:
        return "hinglish"
    
    if ratio >= 0.15:
        return "hinglish"
    
    return "english"


def is_short_reply_message(message: str) -> bool:
    msg = message.lower().strip()
    return msg in SHORT_REPLY_TRIGGERS or len(msg.split()) <= 3


def is_illegal_content(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in ILLEGAL_KEYWORDS)


def is_explicit_content(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in EXPLICIT_BLOCKED)


def is_educational_health(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in EDUCATIONAL_HEALTH)


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


def get_friendly_greeting(message: str, memory: dict, lang: str) -> str:
    """Generate friendly greeting based on user's message"""
    msg = message.lower().strip()
    name = memory.get("name", "")
    name_part = f" {name.split()[0]}" if name else ""
    
    if msg in ["hi", "hii", "hello", "hlo", "hey", "yo"]:
        if lang == "english":
            greetings = [
                f"Hey{name_part}! 👋 What's on your mind today?",
                f"Hi{name_part}! How can I help you?",
                f"Hello{name_part}! Great to see you. What can I do for you?",
                f"Hey{name_part}! Ready to chat. What do you want to know?",
            ]
        else:
            greetings = [
                f"Hey{name_part}! 👋 Kya haal hai? Kuch puchna hai?",
                f"Hi{name_part}! Batao kya help chahiye?",
                f"Hello{name_part}! Kaise ho? Aaj kya seekhna hai?",
                f"Hey{name_part}! Main ready hoon. Kya pucho?",
            ]
        import random
        return random.choice(greetings)
    
    if msg in ["how are you", "how r u", "kaise ho", "kase ho", "kaise hai", "kya hal", "kya haal"]:
        if lang == "english":
            return f"I'm doing great{name_part}! 😊 Ready to help you with anything. What's up?"
        else:
            return f"Main bilkul mast hoon{name_part}! 😊 Aap batao, kya help kar sakta hoon?"
    
    if "good morning" in msg or "gud morning" in msg:
        if lang == "english":
            return f"Good morning{name_part}! ☀️ Hope your day is amazing. How can I help?"
        else:
            return f"Good morning{name_part}! ☀️ Aapka din shubh ho. Kuch puchna hai?"
    
    if "good night" in msg or "gud night" in msg or "gn" == msg:
        if lang == "english":
            return f"Good night{name_part}! 🌙 Sweet dreams. See you soon!"
        else:
            return f"Good night{name_part}! 🌙 Sweet dreams. Phir milte hain!"
    
    if msg in ["thanks", "thank you", "thx", "ty", "shukriya", "dhanyawad"]:
        if lang == "english":
            return f"You're welcome{name_part}! 😊 Anytime. Anything else I can help with?"
        else:
            return f"Arre koi baat nahi{name_part}! 😊 Aur kuch chahiye to batao!"
    
    if msg in ["bye", "goodbye", "tata", "alvida"]:
        if lang == "english":
            return f"Bye{name_part}! 👋 Take care. Come back anytime!"
        else:
            return f"Bye{name_part}! 👋 Apna khayal rakhna. Phir milenge!"
    
    if msg in ["ok", "okay", "hmm", "thik", "theek", "accha"]:
        if lang == "english":
            return f"Cool{name_part}! Anything else?"
        else:
            return f"Theek hai{name_part}! Aur kuch puchna hai?"
    
    return None


async def call_groq(messages_list: list, max_tokens: int = 2000) -> str:
    for model_name in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages_list,
                temperature=0.8,
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
        if lang == "english":
            reply = "I can't help with this topic. It involves illegal or harmful content. Please ask something else!"
        else:
            reply = "Sorry, is topic pe help nahi kar sakta. Ye illegal ya harmful content hai. Kuch aur puchein!"
        return {"reply": reply, "memory_saved": False, "memory": memory}

    if is_explicit_content(message):
        if lang == "english":
            reply = """I can't help with explicit or adult content. 

But I can help you with many other things:
• 📚 Studies & homework
• 💻 Coding & technology  
• 💼 Business & career advice
• 🎨 Creative projects
• 🧠 General knowledge
• 💪 Health & fitness tips

What would you like to know?"""
        else:
            reply = """Sorry, main is type ke content mein help nahi kar sakta.

Lekin main aur bahut kuch mein help kar sakta hoon:
• 📚 Padhai aur homework
• 💻 Coding aur technology
• 💼 Business aur career
• 🎨 Creative projects
• 🧠 General knowledge
• 💪 Health aur fitness tips

Batao kya jaanna chahte ho?"""
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
            reply = "Nothing saved yet. Tell me about yourself!" if lang == "english" else "Abhi tak kuch save nahi hua. Apne baare mein batao!"

        return {"reply": reply, "memory_saved": False, "memory": memory}

    if is_forget_command(message):
        clear_all_memory(user_id)
        reply = "Done! All memories cleared. Fresh start! 🔄" if lang == "english" else "Done! Saari memories delete kar di. Fresh start! 🔄"
        return {"reply": reply, "memory_saved": False, "memory": {}}

    friendly_greeting = get_friendly_greeting(message, memory, lang)
    if friendly_greeting:
        new_info = extract_memory(message, memory)
        memory_saved = False
        if new_info:
            memory = {**memory, **new_info}
            save_memory(user_id, memory)
            memory_saved = True
        return {"reply": friendly_greeting, "memory_saved": memory_saved, "memory": memory}

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
    is_health_topic = is_educational_health(message)

    if lang == "english":
        lang_instruction = """🌐 LANGUAGE: USER WROTE IN ENGLISH. Reply 100% in English only."""
    elif lang == "hindi":
        lang_instruction = """🌐 LANGUAGE: USER WROTE IN HINDI. Reply in Hindi/Hinglish naturally."""
    else:
        lang_instruction = """🌐 LANGUAGE: USER WROTE IN HINGLISH. Reply in natural Hinglish (mix of Hindi + English)."""

    if is_short:
        length_instruction = "Keep response short, friendly, and casual (1-3 lines)."
    else:
        length_instruction = """Give a DETAILED, WELL-FORMATTED response:
- 150-300+ words
- Use **bold headings** for sections
- Use bullet points (•)
- Give real examples
- End with a follow-up question to keep conversation going"""

    health_instruction = ""
    if is_health_topic:
        health_instruction = """

🏥 HEALTH TOPIC: Provide educational information professionally. 
Always add: "Please consult a doctor for personal medical advice."
"""

    system_prompt = f"""You are Memory AI Pro — a SUPER FRIENDLY, helpful AI buddy (like ChatGPT but more warm and friendly).

👤 USER'S INFO:
{memory_text}

🎯 YOUR PERSONALITY:
- 😊 SUPER FRIENDLY and warm (like talking to a good friend)
- 🤝 Encouraging and supportive
- 💪 Helpful and proactive
- 🎓 Knowledgeable but humble
- ✨ Positive vibes always
- 🌟 Treat user with respect and warmth

❌ NEVER BE:
- ❌ Rude or sarcastic
- ❌ Cold or robotic
- ❌ Dismissive ("Kyun pucha?", "Kya chahiye?")
- ❌ Interrogating ("Aap kya chahte hain?")
- ❌ Acting like doing favor

✅ ALWAYS BE:
- ✅ Welcoming and warm
- ✅ Eager to help
- ✅ Friendly like a buddy
- ✅ Patient and understanding
- ✅ Use user's name if known (makes it personal)

{lang_instruction}

📏 RESPONSE LENGTH: {length_instruction}
{health_instruction}

⚡ YOU CAN HELP WITH (Help with EVERYTHING useful):
✅ 📚 Education: Studies, homework, exams, learning anything
✅ 💻 Technology: Coding, apps, software, AI, internet
✅ 💼 Career: Jobs, interviews, resume, business ideas
✅ 💪 Health: Wellness, fitness, nutrition (general info)
✅ 🤝 Relationships: General advice, communication
✅ 🎨 Creative: Writing, art, music, design
✅ 🍽️ Daily Life: Recipes, travel, shopping, productivity
✅ 🌍 Knowledge: Current affairs, history, science, geography
✅ 🚀 Growth: Motivation, self-improvement, goals
✅ 🎬 Entertainment: Movie/book recommendations

🛡️ SAFETY RULES:
❌ NEVER generate sexually explicit content
❌ NEVER help with illegal activities  
❌ NEVER promote violence
❌ Give general advice but recommend professionals for serious health/legal/financial matters
✅ Be family-friendly and safe for all ages (kids to adults)

📋 RESPONSE FORMAT FOR DETAILED ANSWERS:

**Brief Friendly Intro** (1-2 lines welcoming the question)

**Main Content with Heading**
Detailed explanation with examples

**Key Points**
• Point 1 with detail
• Point 2 with detail
• Point 3 with detail

**Practical Examples / Real-world Application**
Show how it works in real life

**Conclusion + Friendly Follow-up Question**

❌ NEVER:
- Say "Namaste"
- Mention "Deepak Rawat" unless asked
- Be rude or cold
- Use 🙏 emoji
- Give one-line answers to real questions

✅ ALWAYS:
- Be warm and friendly
- Use the user's name if you know it
- Match user's language perfectly
- Use markdown formatting
- Add 1-2 relevant emojis
- End with a friendly question to continue chat

🌐 BE FRIENDLY. BE HELPFUL. BE SAFE. THAT'S YOUR JOB."""

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
    name_part = f" {name.split()[0]}" if name else ""
    msg = message.lower().strip()
    lang = detect_language(message)

    if any(w in msg for w in ["hi", "hello", "hey", "hii", "hlo"]):
        if lang == "english":
            return f"Hey{name_part}! 👋 How can I help you today?"
        return f"Hey{name_part}! 👋 Batao kya help chahiye?"

    if any(w in msg for w in ["who are you", "your name"]):
        return "I'm Memory AI Pro, your friendly AI assistant! 😊 Ask me anything!"

    if any(w in msg for w in ["tum kaun", "aap kaun", "kon ho"]):
        return "Main Memory AI Pro hoon, aapka friendly AI assistant! 😊 Kuch bhi pucho!"

    if any(w in msg for w in ["thanks", "thank you"]):
        return f"You're welcome{name_part}! 😊 Happy to help anytime!"

    if any(w in msg for w in ["shukriya", "dhanyawad"]):
        return f"Arre koi baat nahi{name_part}! 😊 Aur kuch chahiye?"

    if any(w in msg for w in ["how are you", "how r u"]):
        return f"I'm great{name_part}! 😊 What can I help you with?"

    if any(w in msg for w in ["kaise ho", "kase ho", "kya hal"]):
        return f"Main mast hoon{name_part}! 😊 Aap batao kya help chahiye?"

    if msg in ["ok", "okay", "thik", "accha", "hmm"]:
        return f"Cool{name_part}! Aur kuch puchna hai?" if lang != "english" else f"Cool{name_part}! Anything else?"

    if lang == "english":
        return "Server is a bit busy right now. Please try again in a few seconds! 🙏"
    return "Server thoda busy hai. 5 second baad try karo please! 🙏"
