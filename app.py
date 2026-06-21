from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# ---------- IN-MEMORY DATABASE ----------
memories_db = {}  # user_id -> list of memories

# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/save", methods=["POST"])
def save_memory():
    data = request.json
    user_id = data.get("user_id", "default")
    memory_text = data.get("text", "").strip()
    category = data.get("category", "general")

    if not memory_text:
        return jsonify({"error": "Empty memory"}), 400

    memory = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "text": memory_text,
        "category": category,
        "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "created_at": datetime.now().isoformat()
    }

    if user_id not in memories_db:
        memories_db[user_id] = []

    memories_db[user_id].append(memory)

    return jsonify({
        "status": "saved",
        "memory": memory,
        "total": len(memories_db[user_id])
    })


@app.route("/api/recall", methods=["POST"])
def recall_memory():
    data = request.json
    user_id = data.get("user_id", "default")
    query = data.get("query", "").lower().strip()

    user_memories = memories_db.get(user_id, [])

    if not query or query in ["all", "sab", "everything", "sab kuch"]:
        return jsonify({
            "results": user_memories[-20:],
            "total": len(user_memories)
        })

    # ---------- SMART SEARCH ----------
    results = []
    for mem in user_memories:
        score = 0
        text_lower = mem["text"].lower()

        # Exact match
        if query in text_lower:
            score += 10

        # Word-by-word match
        query_words = query.split()
        for word in query_words:
            if word in text_lower:
                score += 3

        # Category match
        if query in mem.get("category", "").lower():
            score += 5

        if score > 0:
            results.append({**mem, "_score": score})

    # Sort by relevance
    results.sort(key=lambda x: x["_score"], reverse=True)

    # Remove score from output
    for r in results:
        r.pop("_score", None)

    return jsonify({
        "results": results[:10],
        "total": len(results),
        "query": query
    })


@app.route("/api/delete", methods=["POST"])
def delete_memory():
    data = request.json
    user_id = data.get("user_id", "default")
    memory_id = data.get("id", "")

    user_memories = memories_db.get(user_id, [])
    memories_db[user_id] = [m for m in user_memories if m["id"] != memory_id]

    return jsonify({"status": "deleted"})


@app.route("/api/stats", methods=["POST"])
def get_stats():
    data = request.json
    user_id = data.get("user_id", "default")
    user_memories = memories_db.get(user_id, [])

    categories = {}
    for mem in user_memories:
        cat = mem.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    return jsonify({
        "total_memories": len(user_memories),
        "categories": categories,
        "user_id": user_id
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)