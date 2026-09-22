import os
from datetime import datetime

from flask import Flask, jsonify, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Konfiguration über Umgebungsvariable (12-Factor-Prinzip):
# lokal ohne DATABASE_URL -> SQLite-Datei
# in Azure: DATABASE_URL zeigt auf Azure Database for PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///todos.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(255), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>VICC To-Do-Liste</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #0e7fa3;
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding-top: 2rem;
        }}
        .card {{
            background: rgba(255,255,255,0.1);
            padding: 2rem 3rem;
            border-radius: 12px;
            width: 90%;
            max-width: 480px;
        }}
        h1 {{ margin-top: 0; }}
        form {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }}
        input[type=text] {{
            flex: 1;
            padding: 0.5rem;
            border-radius: 6px;
            border: none;
        }}
        button {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: none;
            background: #f0f0f0;
            cursor: pointer;
        }}
        ul {{ list-style: none; padding: 0; }}
        li {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.08);
            padding: 0.6rem 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        .done {{ text-decoration: line-through; opacity: 0.6; }}
        .actions form {{ margin: 0; display: inline; }}
        .actions button {{ margin-left: 0.3rem; }}
        footer {{ margin-top: 1.5rem; font-size: 0.8rem; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Meine To-Dos</h1>
        <form method="POST" action="/add">
            <input type="text" name="task" placeholder="Neue Aufgabe..." required>
            <button type="submit">Hinzufügen</button>
        </form>
        <ul>
            {items}
        </ul>
        <footer>API: <code>/api/todos</code> &middot; Status: <code>/api/status</code></footer>
    </div>
</body>
</html>
"""

ITEM_TEMPLATE = """
<li>
    <span class="{cls}">{task}</span>
    <span class="actions">
        <form method="POST" action="/complete/{id}"><button>{toggle_label}</button></form>
        <form method="POST" action="/delete/{id}"><button>Löschen</button></form>
    </span>
</li>
"""


def render_items():
    todos = Todo.query.order_by(Todo.created_at.desc()).all()
    if not todos:
        return "<li>Keine Aufgaben vorhanden.</li>"
    html = ""
    for t in todos:
        html += ITEM_TEMPLATE.format(
            cls="done" if t.done else "",
            task=t.task,
            id=t.id,
            toggle_label="Erledigt" if not t.done else "Zurücksetzen",
        )
    return html


@app.route("/")
def index():
    return PAGE_TEMPLATE.format(items=render_items())


@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task", "").strip()
    if task:
        db.session.add(Todo(task=task))
        db.session.commit()
    return redirect(url_for("index"))


@app.route("/complete/<int:todo_id>", methods=["POST"])
def complete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    todo.done = not todo.done
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/api/todos")
def api_todos():
    todos = Todo.query.order_by(Todo.created_at.desc()).all()
    return jsonify([
        {"id": t.id, "task": t.task, "done": t.done, "created_at": t.created_at.isoformat()}
        for t in todos
    ])


@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "ok",
        "database": "sqlite (lokal)" if DATABASE_URL.startswith("sqlite") else "postgresql (cloud)",
        "todo_count": Todo.query.count(),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
