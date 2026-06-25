from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import asyncio
import json
import os
import uuid

from chat import process_message
from memory import (
    get_memory, save_memory, delete_memory, clear_all_memory,
    delete_memory_field, update_memory_field, get_all_memories,
    save_chat_message, get_chat_history, get_user_chats,
    create_chat_session, update_chat_title, delete_chat_session,
    clear_user_chats, save_feedback, get_all_feedback,
    get_user_stats, reset_database
)

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return "", 200
    return send_from_directory(".", "index.html")


@app.route("/health", methods=["GET", "HEAD"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Memory AI Pro",
        "version": "2.1",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        message = data.get("message", "").strip()
        chat_id = data.get("chat_id", "")

        if not message:
            return jsonify({"error": "Message empty hai"}), 400

        if not chat_id:
            chat_id = f"chat_{uuid.uuid4().hex[:12]}"
            create_chat_session(user_id, chat_id, "New Chat")

        # 🧠 Get conversation history BEFORE saving new message
        history = get_chat_history(chat_id, limit=20)

        # Save user message
        save_chat_message(user_id, chat_id, "user", message)

        # Process with history context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_message(user_id, message, history))
        loop.close()

        reply = result.get("reply", "Server busy hai")
        memory_saved = result.get("memory_saved", False)
        memory = result.get("memory", {})

        # Save AI reply
        save_chat_message(user_id, chat_id, "assistant", reply)

        # Auto-generate title
        full_history = get_chat_history(chat_id)
        if len(full_history) == 2:
            title = generate_chat_title(message)
            update_chat_title(chat_id, title)

        return jsonify({
            "reply": reply,
            "chat_id": chat_id,
            "memory_saved": memory_saved,
            "memory": memory,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({
            "error": "Kuch problem hui, kripya phir try karein",
            "details": str(e)
        }), 500


def generate_chat_title(first_message: str) -> str:
    msg = first_message.strip()
    greetings = ["hi", "hello", "hey", "namaste", "hii", "hlo"]
    if msg.lower() in greetings:
        return "Greeting Chat"
    words = msg.split()[:5]
    title = " ".join(words)
    if len(title) > 35:
        title = title[:32] + "..."
    return title.capitalize() if title else "New Chat"


@app.route("/api/memory/get", methods=["POST"])
def api_get_memory():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        memory = get_memory(user_id)
        return jsonify({"memory": memory, "count": len(memory), "user_id": user_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/update", methods=["POST"])
def api_update_memory():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        field = data.get("field", "")
        value = data.get("value", "")
        if not field:
            return jsonify({"error": "Field zaroori hai"}), 400
        success = update_memory_field(user_id, field, value)
        return jsonify({"status": "updated" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/delete-field", methods=["POST"])
def api_delete_memory_field():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        field = data.get("field", "")
        success = delete_memory_field(user_id, field)
        return jsonify({"status": "deleted" if success else "not_found"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/clear", methods=["POST"])
def api_clear_memory():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        success = clear_all_memory(user_id)
        return jsonify({"status": "cleared" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/list", methods=["POST"])
def api_get_user_chats():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        chats = get_user_chats(user_id)
        return jsonify({"chats": chats, "count": len(chats)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/history", methods=["POST"])
def api_get_chat_history():
    try:
        data = request.json
        chat_id = data.get("chat_id", "")
        if not chat_id:
            return jsonify({"error": "chat_id zaroori hai"}), 400
        history = get_chat_history(chat_id)
        return jsonify({"history": history, "count": len(history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/delete", methods=["POST"])
def api_delete_chat():
    try:
        data = request.json
        chat_id = data.get("chat_id", "")
        success = delete_chat_session(chat_id)
        return jsonify({"status": "deleted" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/clear", methods=["POST"])
def api_clear_chats():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        success = clear_user_chats(user_id)
        return jsonify({"status": "cleared" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/rename", methods=["POST"])
def api_rename_chat():
    try:
        data = request.json
        chat_id = data.get("chat_id", "")
        new_title = data.get("title", "").strip()
        if not chat_id or not new_title:
            return jsonify({"error": "chat_id aur title zaroori hain"}), 400
        success = update_chat_title(chat_id, new_title)
        return jsonify({"status": "renamed" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def api_save_feedback():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        rating = int(data.get("rating", 0))
        message = data.get("message", "").strip()
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating 1-5 ke beech honi chahiye"}), 400
        success = save_feedback(user_id, rating, message)
        return jsonify({"status": "saved" if success else "failed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["POST"])
def api_get_stats():
    try:
        data = request.json
        user_id = data.get("user_id", "default")
        stats = get_user_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json")


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(".", "service-worker.js")


@app.route("/icon-192.png")
def icon_192():
    return send_from_directory(".", "icon-192.png")


@app.route("/icon-152.png")
def icon_152():
    return send_from_directory(".", "icon-152.png")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/api/admin/all-memories", methods=["GET"])
def admin_all_memories():
    memories = get_all_memories()
    return jsonify({"memories": memories, "count": len(memories)})


@app.route("/api/admin/all-feedback", methods=["GET"])
def admin_all_feedback():
    feedback = get_all_feedback()
    return jsonify({"feedback": feedback, "count": len(feedback)})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint nahi mila"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error", "details": str(e)}), 500


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method allowed nahi hai"}), 405


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Memory AI Pro starting on port {port}")
    print(f"💾 Database: SQLite (memory.db)")
    print(f"🤖 AI: Groq")
    app.run(host="0.0.0.0", port=port, debug=False)
