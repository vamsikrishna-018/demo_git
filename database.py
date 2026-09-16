import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "todo.db"


class DatabaseManager:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_db():
        conn = DatabaseManager.get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                priority TEXT NOT NULL DEFAULT 'Medium',
                category TEXT NOT NULL DEFAULT 'Other',
                due_date TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                theme TEXT NOT NULL DEFAULT 'light',
                accent_color TEXT NOT NULL DEFAULT '#4f46e5'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                icon TEXT NOT NULL,
                unlocked INTEGER NOT NULL DEFAULT 0,
                earned_at TEXT
            )
            """
        )
        conn.commit()
        DatabaseManager.seed_defaults(conn)
        conn.close()

    @staticmethod
    def seed_defaults(conn):
        default_categories = [
            "College",
            "Personal",
            "Work",
            "Shopping",
            "Other",
        ]
        now = datetime.utcnow().isoformat()
        for category in default_categories:
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, created_at) VALUES (?, ?)",
                (category, now),
            )

        conn.execute(
            "INSERT OR IGNORE INTO user_settings (id, theme, accent_color) VALUES (1, 'light', '#4f46e5')"
        )

        achievements = [
            ("First Task", "Complete your first task.", "🏅"),
            ("5-Day Streak", "Complete tasks for 5 consecutive days.", "🔥"),
            ("Task Master", "Complete 50 tasks.", "🎯"),
            ("Speed Runner", "Complete 5 tasks in one day.", "⚡"),
        ]
        for name, description, icon in achievements:
            conn.execute(
                "INSERT OR IGNORE INTO achievements (name, description, icon, unlocked) VALUES (?, ?, ?, 0)",
                (name, description, icon),
            )

        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            today = date.today().isoformat()
            sample_tasks = [
                (
                    "Complete project proposal",
                    "Finish the client proposal and review the final draft.",
                    0,
                    "High",
                    "College",
                    today,
                    now,
                    None,
                ),
                (
                    "Book grocery items",
                    "Buy fruits, milk, and lunch ingredients for the week.",
                    0,
                    "Medium",
                    "Shopping",
                    (date.today() + timedelta(days=1)).isoformat(),
                    now,
                    None,
                ),
                (
                    "Prepare for interview",
                    "Review common questions and practice answers for 20 minutes.",
                    0,
                    "High",
                    "Work",
                    date.today().isoformat(),
                    now,
                    None,
                ),
            ]
            conn.executemany(
                """
                INSERT INTO tasks (title, description, completed, priority, category, due_date, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sample_tasks,
            )

        conn.commit()

    @staticmethod
    def add_task(data):
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        priority = (data.get("priority") or "Medium").strip() or "Medium"
        category = (data.get("category") or "Other").strip() or "Other"
        due_date = data.get("due_date")
        created_at = datetime.utcnow().isoformat()

        if not title:
            raise ValueError("Task title is required.")
        if priority not in {"High", "Medium", "Low"}:
            raise ValueError("Invalid priority value.")

        conn = DatabaseManager.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, description, completed, priority, category, due_date, created_at, completed_at)
            VALUES (?, ?, 0, ?, ?, ?, ?, NULL)
            """,
            (title, description, priority, category, due_date, created_at),
        )
        task_id = cursor.lastrowid
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.commit()
        conn.close()
        return dict(task)

    @staticmethod
    def list_tasks(search=None, filter_name="all", sort_by="newest"):
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if search:
            search_term = f"%{search.lower()}%"
            query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)"
            params.extend([search_term, search_term, search_term])

        if filter_name == "active":
            query += " AND completed = 0"
        elif filter_name == "completed":
            query += " AND completed = 1"
        elif filter_name == "today":
            query += " AND due_date = ?"
            params.append(date.today().isoformat())
        elif filter_name == "overdue":
            query += " AND completed = 0 AND due_date IS NOT NULL AND due_date < ?"
            params.append(date.today().isoformat())
        elif filter_name == "high":
            query += " AND priority = 'High'"

        if sort_by == "oldest":
            query += " ORDER BY created_at ASC"
        elif sort_by == "priority":
            query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END ASC, created_at DESC"
        elif sort_by == "due_date":
            query += " ORDER BY due_date IS NULL, due_date ASC, created_at DESC"
        elif sort_by == "alphabetical":
            query += " ORDER BY title COLLATE NOCASE ASC"
        else:
            query += " ORDER BY created_at DESC"

        conn = DatabaseManager.get_connection()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def update_task(task_id, data):
        conn = DatabaseManager.get_connection()
        existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if existing is None:
            conn.close()
            raise KeyError("Task not found.")

        title = (data.get("title") or existing["title"]).strip()
        description = (data.get("description") or existing["description"]).strip()
        priority = (data.get("priority") or existing["priority"]).strip() or existing["priority"]
        category = (data.get("category") or existing["category"]).strip() or existing["category"]
        due_date = data.get("due_date", existing["due_date"])
        completed = int(bool(data.get("completed", bool(existing["completed"]))))
        now = datetime.utcnow().isoformat()
        completed_at = now if completed and existing["completed"] == 0 else (existing["completed_at"] if completed else None)

        if not title:
            conn.close()
            raise ValueError("Task title is required.")

        conn.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, category = ?, due_date = ?, completed = ?, completed_at = ?
            WHERE id = ?
            """,
            (title, description, priority, category, due_date, completed, completed_at, task_id),
        )
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.commit()
        conn.close()
        return dict(updated)

    @staticmethod
    def delete_task(task_id):
        conn = DatabaseManager.get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            conn.close()
            raise KeyError("Task not found.")
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return dict(task)

    @staticmethod
    def complete_task(task_id):
        conn = DatabaseManager.get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            conn.close()
            raise KeyError("Task not found.")
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.commit()
        conn.close()
        return dict(updated)

    @staticmethod
    def restore_task(task_id):
        conn = DatabaseManager.get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            conn.close()
            raise KeyError("Task not found.")
        conn.execute(
            "UPDATE tasks SET completed = 0, completed_at = NULL WHERE id = ?",
            (task_id,),
        )
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.commit()
        conn.close()
        return dict(updated)

    @staticmethod
    def delete_completed_tasks():
        conn = DatabaseManager.get_connection()
        conn.execute("DELETE FROM tasks WHERE completed = 1")
        conn.commit()
        conn.close()

    @staticmethod
    def list_categories():
        conn = DatabaseManager.get_connection()
        rows = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def create_category(name):
        category_name = (name or "").strip()
        if not category_name:
            raise ValueError("Category name is required.")
        conn = DatabaseManager.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                (category_name, datetime.utcnow().isoformat()),
            )
            category = conn.execute("SELECT * FROM categories WHERE id = ?", (cursor.lastrowid,)).fetchone()
            conn.commit()
            conn.close()
            return dict(category)
        except sqlite3.IntegrityError as exc:
            conn.close()
            raise ValueError("Category already exists.") from exc

    @staticmethod
    def delete_category(category_id):
        conn = DatabaseManager.get_connection()
        category = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category is None:
            conn.close()
            raise KeyError("Category not found.")
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.execute(
            "UPDATE tasks SET category = 'Other' WHERE category = ?",
            (category["name"],),
        )
        conn.commit()
        conn.close()
        return dict(category)

    @staticmethod
    def get_settings():
        conn = DatabaseManager.get_connection()
        row = conn.execute("SELECT * FROM user_settings WHERE id = 1").fetchone()
        conn.close()
        if row is None:
            return {"theme": "light", "accent_color": "#4f46e5"}
        return {"theme": row["theme"], "accent_color": row["accent_color"]}

    @staticmethod
    def save_settings(theme, accent_color):
        payload_theme = (theme or "light").strip() or "light"
        payload_accent = (accent_color or "#4f46e5").strip() or "#4f46e5"
        conn = DatabaseManager.get_connection()
        conn.execute(
            "INSERT INTO user_settings (id, theme, accent_color) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET theme=excluded.theme, accent_color=excluded.accent_color",
            (payload_theme, payload_accent),
        )
        conn.commit()
        conn.close()
        return {"theme": payload_theme, "accent_color": payload_accent}

    @staticmethod
    def get_statistics():
        conn = DatabaseManager.get_connection()
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 0").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1").fetchone()[0]
        today = date.today().isoformat()
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 0 AND due_date IS NOT NULL AND due_date < ?",
            (today,),
        ).fetchone()[0]
        weekly = []
        for offset in range(7):
            target_day = (date.today() - timedelta(days=6 - offset)).isoformat()
            value = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
                (target_day,),
            ).fetchone()[0]
            weekly.append({"day": target_day, "label": target_day[5:], "count": value})
        conn.close()
        productivity = 0
        if total:
            productivity = round((completed / total) * 100)
        return {
            "total": total,
            "active": active,
            "completed": completed,
            "overdue": overdue,
            "productivity": productivity,
            "weekly": weekly,
        }

    @staticmethod
    def get_insights():
        conn = DatabaseManager.get_connection()
        high_remaining = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 0 AND priority = 'High'"
        ).fetchone()[0]
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 0 AND due_date IS NOT NULL AND due_date < ?",
            (date.today().isoformat(),),
        ).fetchone()[0]
        completed_this_week = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) >= ?",
            ((date.today() - timedelta(days=6)).isoformat(),),
        ).fetchone()[0]
        today = date.today().isoformat()
        tasks_done_today = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tasks_done_yesterday = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
            (yesterday,),
        ).fetchone()[0]
        conn.close()

        insights = []
        if high_remaining:
            insights.append(f"💡 You have {high_remaining} high-priority tasks remaining.")
        if overdue:
            insights.append(f"⚠️ You have {overdue} overdue tasks.")
        if completed_this_week:
            insights.append(f"🎯 You completed {completed_this_week} tasks this week.")
        if tasks_done_today > tasks_done_yesterday:
            insights.append("🔥 Great job! You completed more tasks today than yesterday.")
        if not insights:
            insights.append("🌱 Your plan is clear. Start with one small task to build momentum.")
        return insights

    @staticmethod
    def get_achievements():
        conn = DatabaseManager.get_connection()
        total_completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1").fetchone()[0]
        all_rows = conn.execute("SELECT * FROM achievements ORDER BY id ASC").fetchall()
        streak = DatabaseManager.calculate_streak(conn)
        rows = []
        for row in all_rows:
            unlocked = False
            if row["name"] == "First Task" and total_completed >= 1:
                unlocked = True
            elif row["name"] == "5-Day Streak" and streak >= 5:
                unlocked = True
            elif row["name"] == "Task Master" and total_completed >= 50:
                unlocked = True
            elif row["name"] == "Speed Runner":
                today = date.today().isoformat()
                today_count = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
                    (today,),
                ).fetchone()[0]
                unlocked = today_count >= 5
            rows.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "icon": row["icon"],
                    "unlocked": unlocked,
                }
            )
        conn.close()
        return rows

    @staticmethod
    def calculate_streak(conn):
        current = date.today()
        streak = 0
        while True:
            day = current.isoformat()
            count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
                (day,),
            ).fetchone()[0]
            if count > 0:
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak

    @staticmethod
    def export_tasks():
        conn = DatabaseManager.get_connection()
        rows = conn.execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def import_tasks(items):
        if not isinstance(items, list):
            raise ValueError("Imported data must be a list of task objects.")
        conn = DatabaseManager.get_connection()
        inserted = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each imported item must be an object.")
            title = str(item.get("title") or "").strip()
            if not title:
                raise ValueError("Every imported task must have a title.")
            description = str(item.get("description") or "")
            priority = str(item.get("priority") or "Medium")
            category = str(item.get("category") or "Other")
            due_date = item.get("due_date")
            completed = int(bool(item.get("completed", False)))
            created_at = item.get("created_at") or datetime.utcnow().isoformat()
            completed_at = item.get("completed_at")
            cursor = conn.execute(
                """
                INSERT INTO tasks (title, description, completed, priority, category, due_date, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, description, completed, priority, category, due_date, created_at, completed_at),
            )
            inserted.append(cursor.lastrowid)
        conn.commit()
        conn.close()
        return inserted
