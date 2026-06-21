# memory.py — Fixed Version

import sqlite3
import json
import os

DB_PATH = "memory_ai.db"

# ═══════════════════════════════════
#       DATABASE INIT
# ═══════════════════════════════════
def init_db():
    """Database aur table banao agar exist nahi karta"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            age TEXT,
            work TEXT,
            hobby TEXT,
            favorite_food TEXT,
            extra_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database Ready!")

# Database initialize karo jab file load ho
init_db()


# ═══════════════════════════════════
#       GET MEMORY
# ═══════════════════════════════════
def get_memory(user_id: str) -> dict:
    """User ki memory load karo database se"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, name, age, work, hobby, favorite_food, extra_info
            FROM memories 
            WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "user_id": row[0],
                "name": row[1] or "",
                "age": row[2] or "",
                "work": row[3] or "",
                "hobby": row[4] or "",
                "favorite_food": row[5] or "",
                "extra_info": row[6] or ""
            }
        else:
            return {
                "user_id": user_id,
                "name": "",
                "age": "",
                "work": "",
                "hobby": "",
                "favorite_food": "",
                "extra_info": ""
            }
    except Exception as e:
        print(f"❌ Get Memory Error: {e}")
        return {"user_id": user_id, "name": "", "age": "", 
                "work": "", "hobby": "", "favorite_food": "", "extra_info": ""}


# ═══════════════════════════════════
#       SAVE MEMORY
# ═══════════════════════════════════
def save_memory(user_id: str, data: dict) -> bool:
    """User ki memory save/update karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories (user_id, name, age, work, hobby, favorite_food, extra_info, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                name = COALESCE(NULLIF(excluded.name, ''), memories.name),
                age = COALESCE(NULLIF(excluded.age, ''), memories.age),
                work = COALESCE(NULLIF(excluded.work, ''), memories.work),
                hobby = COALESCE(NULLIF(excluded.hobby, ''), memories.hobby),
                favorite_food = COALESCE(NULLIF(excluded.favorite_food, ''), memories.favorite_food),
                extra_info = COALESCE(NULLIF(excluded.extra_info, ''), memories.extra_info),
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            data.get("name", ""),
            data.get("age", ""),
            data.get("work", ""),
            data.get("hobby", ""),
            data.get("favorite_food", ""),
            data.get("extra_info", "")
        ))
        conn.commit()
        conn.close()
        print(f"💾 Memory Saved for {user_id}")
        return True
    except Exception as e:
        print(f"❌ Save Memory Error: {e}")
        return False


# ═══════════════════════════════════
#       GET ALL MEMORIES
# ═══════════════════════════════════
def get_all_memories() -> list:
    """Saari memories fetch karo (admin ke liye)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, name, age, work, hobby, favorite_food, extra_info, updated_at
            FROM memories
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        memories = []
        for row in rows:
            memories.append({
                "user_id": row[0],
                "name": row[1] or "",
                "age": row[2] or "",
                "work": row[3] or "",
                "hobby": row[4] or "",
                "favorite_food": row[5] or "",
                "extra_info": row[6] or "",
                "updated_at": row[7] or ""
            })
        return memories
    except Exception as e:
        print(f"❌ Get All Memories Error: {e}")
        return []


# ═══════════════════════════════════
#       DELETE MEMORY
# ═══════════════════════════════════
def delete_memory(user_id: str) -> bool:
    """User ki memory delete karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        print(f"🗑️ Memory Deleted for {user_id}")
        return True
    except Exception as e:
        print(f"❌ Delete Memory Error: {e}")
        return False