import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "memory.db"


def init_db():
    """Database initialize karo"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Main memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chat history table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chat sessions table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            chat_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Feedback table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            rating INTEGER,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database Ready!")


# ============ MEMORY FUNCTIONS ============

def get_memory(user_id: str) -> dict:
    """User ki memory laao"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM memories WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        try:
            return json.loads(row[0])
        except:
            return {}
    return {}


def save_memory(user_id: str, memory_data: dict) -> bool:
    """User ki memory save karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        data_json = json.dumps(memory_data, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO memories (user_id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, data_json))
        
        conn.commit()
        conn.close()
        print(f"💾 Memory Saved for {user_id}")
        return True
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False


def get_all_memories() -> list:
    """Saari memories laao"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, data, updated_at FROM memories")
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            try:
                memories.append({
                    "user_id": row[0],
                    "data": json.loads(row[1]),
                    "updated_at": row[2]
                })
            except:
                continue
        return memories
    except Exception as e:
        print(f"❌ Get all error: {e}")
        return []


def delete_memory(user_id: str) -> bool:
    """Ek user ki saari memory delete karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        print(f"🗑️ Deleted memory for {user_id}")
        return True
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return False


def clear_all_memory(user_id: str) -> bool:
    """User ki saari memory clear karo (alias for delete_memory)"""
    return delete_memory(user_id)


def delete_memory_field(user_id: str, field: str) -> bool:
    """Specific field delete karo (jaise name, age, etc.)"""
    try:
        memory = get_memory(user_id)
        if field in memory:
            del memory[field]
            save_memory(user_id, memory)
            print(f"🗑️ Deleted field '{field}' for {user_id}")
            return True
        return False
    except Exception as e:
        print(f"❌ Delete field error: {e}")
        return False


def update_memory_field(user_id: str, field: str, value: str) -> bool:
    """Specific field update karo"""
    try:
        memory = get_memory(user_id)
        memory[field] = value
        save_memory(user_id, memory)
        return True
    except Exception as e:
        print(f"❌ Update field error: {e}")
        return False


def get_memory_count(user_id: str) -> int:
    """User ki memory count nikalo"""
    memory = get_memory(user_id)
    return len(memory)


def reset_database() -> bool:
    """Saari memories delete karo (admin function)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        cursor.execute("DELETE FROM chat_history")
        cursor.execute("DELETE FROM chat_sessions")
        conn.commit()
        conn.close()
        print("🧹 Database cleared!")
        return True
    except Exception as e:
        print(f"❌ Reset error: {e}")
        return False


# ============ CHAT HISTORY FUNCTIONS (NEW) ============

def save_chat_message(user_id: str, chat_id: str, role: str, message: str) -> bool:
    """Chat message save karo (role: 'user' or 'assistant')"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (user_id, chat_id, role, message)
            VALUES (?, ?, ?, ?)
        """, (user_id, chat_id, role, message))
        
        # Update session timestamp
        cursor.execute("""
            UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (chat_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Save chat error: {e}")
        return False


def get_chat_history(chat_id: str, limit: int = 50) -> list:
    """Specific chat ki history laao"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, message, created_at FROM chat_history
            WHERE chat_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (chat_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [{"role": r[0], "message": r[1], "time": r[2]} for r in rows]
    except Exception as e:
        print(f"❌ Get chat history error: {e}")
        return []


def get_user_chats(user_id: str) -> list:
    """User ke saare chat sessions laao (sidebar ke liye)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_id, title, updated_at FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{"chat_id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]
    except Exception as e:
        print(f"❌ Get user chats error: {e}")
        return []


def create_chat_session(user_id: str, chat_id: str, title: str = "New Chat") -> bool:
    """Naya chat session create karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO chat_sessions (chat_id, user_id, title)
            VALUES (?, ?, ?)
        """, (chat_id, user_id, title))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Create session error: {e}")
        return False


def update_chat_title(chat_id: str, new_title: str) -> bool:
    """Chat ka title update karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (new_title, chat_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Update title error: {e}")
        return False


def delete_chat_session(chat_id: str) -> bool:
    """Chat session aur uski history delete karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        print(f"🗑️ Deleted chat: {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Delete chat error: {e}")
        return False


def clear_user_chats(user_id: str) -> bool:
    """User ke saare chats delete karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM chat_history WHERE chat_id IN 
            (SELECT chat_id FROM chat_sessions WHERE user_id = ?)
        """, (user_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Clear user chats error: {e}")
        return False


# ============ FEEDBACK FUNCTIONS (NEW) ============

def save_feedback(user_id: str, rating: int, message: str = "") -> bool:
    """User feedback save karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (user_id, rating, message)
            VALUES (?, ?, ?)
        """, (user_id, rating, message))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Save feedback error: {e}")
        return False


def get_all_feedback() -> list:
    """Saara feedback laao (admin ke liye)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, rating, message, created_at FROM feedback
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [{"user_id": r[0], "rating": r[1], "message": r[2], "time": r[3]} for r in rows]
    except Exception as e:
        print(f"❌ Get feedback error: {e}")
        return []


# ============ STATS FUNCTIONS (NEW) ============

def get_user_stats(user_id: str) -> dict:
    """User ke stats (memory count, chat count, etc.)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total chats
        cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?", (user_id,))
        chat_count = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,))
        msg_count = cursor.fetchone()[0]
        
        conn.close()
        
        memory = get_memory(user_id)
        
        return {
            "memory_count": len(memory),
            "chat_count": chat_count,
            "message_count": msg_count,
            "memories": memory
        }
    except Exception as e:
        print(f"❌ Get stats error: {e}")
        return {"memory_count": 0, "chat_count": 0, "message_count": 0, "memories": {}}


# Initialize database on import
init_db()
