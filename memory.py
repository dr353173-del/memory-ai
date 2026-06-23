import sqlite3
import json
import os

DB_PATH = "memory.db"


def init_db():
    """Database initialize kar"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database Ready!")


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
    """User ki memory save kar"""
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
    """Ek user ki memory delete kar"""
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


def reset_database() -> bool:
    """Saari memories delete kar de"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()
        print("🧹 Database cleared!")
        return True
    except Exception as e:
        print(f"❌ Reset error: {e}")
        return False


# Initialize database on import
init_db()
