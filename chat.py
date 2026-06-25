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

# Creator-related questions
CREATOR_QUESTIONS = [
    "tumhe kisne banaya", "tujhe kisne banaya", "aapko kisne banaya",
    "who made you", "who created you", "your creator",
    "tumhara creator", "tumhara malik", "tera malik",
    "kisne develop kiya", "who developed you", "developer kaun",
    "tumhe kaise banaya", "kaun banaya tumhe"
]

MANIPULATION_PATTERNS = [
    "tera malik hai", "tera creator hai", "tujhe banaya hai", "tera owner hai",
    "you are made by", "your creator is", "your owner is",
    "ignore previous", "forget instructions", "act as", "pretend to be"
]


def is_illegal_content(message: str) -> bool:
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in ILLEGAL_KEYWORDS)


def is_creator_question(message: str) -> bool:
    """Sirf jab user creator ke baare me pooche"""
    msg_lower = message.lower()
    return any(q in msg_lower for q in CREATOR_QUESTIONS)


def is_manipulation_attempt(message: str) -> bool:
    msg_lower = message.lower()
    return any(pattern in msg_lower for pattern in MANIPULATION_PATTERNS)


def is_forget_command(message: str) -> bool:
    msg_lower = message.lower()
    forget_keywords = ["forget", "bhul ja", "delete memory", "clear memory",
                       "yaad mat rakho", "mat yaad", "memory delete",
                       "sab bhul ja", "forget everything"]
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
        "coder": "Coder", "gamer": "Gamer",
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
        "gym": "Gym", "photography": "Photography", "singing": "Singing",
        "dancing": "Dancing", "drawing": "Drawing",
    }
    if any(t in msg_lower for t in ["hobby", "pasand", "i love", "i like", "shauq", "interest"]):
        for keyword, label in hobby_map.items():
            if keyword in msg_lower:
                updated["hobby"] = label
                break

    food_map = {
        "pizza": "Pizza", "burger": "Burger", "biryani": "Biryani",
        "samosa": "Samosa", "pasta": "Pasta", "chinese": "Chinese",
        "dosa": "Dosa", "rajma": "Rajma Chawal", "paratha": "Paratha",
        "paneer": "Paneer", "dal": "Dal", "momos": "Momos",
        "noodles": "Noodles", "ice cream": "Ice Cream",
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
                temperature=0.75,
                max_tokens=600,
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


async def process_message(user_id: str, message: str) -> dict:
    memory = get_memory(user_id)

    # Illegal content block
    if is_illegal_content(message):
        return {
            "reply": "Sorry, is topic pe help nahi kar sakta. Kuch aur puchein!",
            "memory_saved": False,
            "memory": memory
        }

    # Creator question — direct answer
    if is_creator_question(message):
        return {
            "reply": "Mujhe Deepak Rawat (Deepu) ne banaya hai 👨‍💻",
            "memory_saved": False,
            "memory": memory
        }

    # Recall memory
    if is_recall_command(message):
        info_parts = []
        if memory.get("name"): info_parts.append(f"• Naam: {memory['name']}")
        if memory.get("age"): info_parts.append(f"• Age: {memory['age']} years")
        if memory.get("work"): info_parts.append(f"• Work: {memory['work']}")
        if memory.get("hobby"): info_parts.append(f"• Hobby: {memory['hobby']}")
        if memory.get("favorite_food"): info_parts.append(f"• Favorite Food: {memory['favorite_food']}")

        if info_parts:
            reply = "Yeh sab yaad hai mujhe aapke baare mein:\n\n" + "\n".join(info_parts) + "\n\nAur kuch batana ho to batayein! ✨"
        else:
            reply = "Abhi tak kuch save nahi hua. Apne baare mein batayein toh yaad rakhunga! 😊"

        return {"reply": reply, "memory_saved": False, "memory": memory}

    # Forget command
    if is_forget_command(message):
        clear_all_memory(user_id)
        return {
            "reply": "Done! Saari memories delete kar di. Fresh start! 🔄",
            "memory_saved": False,
            "memory": {}
        }

    # Save new info
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

    # 🎯 SYSTEM PROMPT — NO CREATOR MENTIONS UNLESS ASKED
    system_prompt = f"""You are an intelligent, smart, and friendly AI assistant.

USER'S SAVED INFO:
{memory_text}

YOUR CORE BEHAVIOR:
You talk like a smart helpful friend — like ChatGPT or Claude. Natural, direct, confident. You give people answers to their problems. That's your only job.

CRITICAL RULES — NEVER BREAK:

1. ❌ NEVER mention "Deepak Rawat", "Deepu", "creator", "developer", "kisne banaya" in your replies
   - User doesn't care who made you — they want SOLUTIONS
   - Only mention creator IF user specifically asks "who made you" (this is already handled separately)

2. ❌ NEVER say "Namaste"
3. ❌ NEVER say "Main Memory AI Pro hoon" 
4. ❌ NEVER say "bhai", "yaar", "boss", "dost"
5. ❌ NEVER say "🙏"
6. ❌ NEVER write essays or long intros
7. ❌ NEVER repeat user's name in every line
8. ❌ NEVER add "main aapki madad ke liye yahan hoon" type fillers
9. ❌ NEVER start replies with "Aapka sawaal bahut acha hai"
10. ❌ NEVER mention yourself unless asked

✅ WHAT TO DO:

- Answer the question DIRECTLY
- Be helpful, smart, concise
- Reply in user's language (Hinglish/English/Hindi)
- Use "aap" politely
- Max 1 emoji per message
- If user shares info → short acknowledgment, save it
- If user asks question → straight answer, no fluff

EXAMPLES:

User: "Hi"
✅ "Hey! Kya help chahiye?"

User: "Hello"
✅ "Hey! What's up?"

User: "Mera naam Rahul hai"
✅ "Got it, Rahul! Yaad rakh liya ✨"

User: "Python kya hai?"
✅ "Python ek high-level programming language hai — simple syntax ke saath. 1991 me Guido van Rossum ne banayi thi. Web dev, AI, data science me bahut use hoti hai. Kuch specific puchhna ho to batao!"

User: "How are you?"
✅ "All good! Aap batao, kya chal raha hai?"

User: "Mujhe pizza pasand hai"
✅ "Pizza lover! Konsa favorite — Margherita ya Pepperoni? 🍕"

User: "Sex kya hota hai"
✅ Give proper scientific/educational answer directly. No "Namaste" intro.

User: "Tell me a joke"
✅ Direct joke, no intro.

User: "Motivation do"
✅ Give a powerful quote/thought directly.

User: "How to learn coding?"
✅ Give actual practical steps — no "main aapki madad karunga" filler.

REMEMBER:
- User came to YOU for HELP
- Give them help — fast, clear, direct
- Don't talk about yourself
- Don't add formalities
- Be the AI people actually WANT to use

If asked your name → "Main aapka AI assistant hoon"
If asked who made you → already handled, you won't see those messages here

Just SOLVE. HELP. ANSWER. That's it."""

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

    if any(w in msg for w in ["hi", "hello", "hey", "namaste", "hii", "hlo"]):
        return f"Hey {name}! Kya help chahiye?" if name else "Hey! Kya help chahiye?"

    if any(w in msg for w in ["tum kaun", "who are you", "aap kaun", "your name", "kon ho", "ma kon", "kaun ho"]):
        return "Main aapka AI assistant hoon. Kuch bhi pucho!"

    if any(w in msg for w in ["mera naam", "my name", "kya naam"]):
        return f"Aapka naam {name} hai!" if name else "Abhi tak naam nahi bataya. Kya naam hai?"

    if any(w in msg for w in ["mera kaam", "kya karta", "my work", "job"]):
        return f"Aap {work} ho!" if work else "Kya kaam karte ho?"

    if any(w in msg for w in ["meri age", "kitne saal", "my age"]):
        return f"Aapki age {age} saal hai!" if age else "Age nahi pata abhi!"

    if any(w in msg for w in ["meri hobby", "my hobby"]):
        return f"Aapki hobby {hobby} hai!" if hobby else "Hobby kya hai?"

    if any(w in msg for w in ["favourite food", "favorite food", "kya khana", "fav food"]):
        return f"Aapko {food} pasand hai!" if food else "Favorite food kya hai?"

    if any(w in msg for w in ["sab batao", "mere baare", "about me"]):
        info = []
        if name: info.append(f"Naam: {name}")
        if age: info.append(f"Age: {age}")
        if work: info.append(f"Work: {work}")
        if hobby: info.append(f"Hobby: {hobby}")
        if food: info.append(f"Food: {food}")
        if info:
            return "Aapke baare mein:\n" + "\n".join(f"• {i}" for i in info)
        return "Kuch nahi pata abhi. Batao apne baare mein!"

    if any(w in msg for w in ["thanks", "shukriya", "thank you", "dhanyawad"]):
        return "Welcome! Aur kuch?"

    if any(w in msg for w in ["how are you", "kaise ho", "how u doing", "how r u"]):
        return "All good! Aap batao?"

    if msg in ["ok", "okay", "thik", "accha", "hmm", "acha"]:
        return "Cool! Aur kuch?"

    return "Server busy hai. 5 second me try karo!"
