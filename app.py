from __future__ import annotations

from flask import Flask, jsonify, request, render_template

from database import DatabaseManager

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    search = request.args.get("search", "")
    active_filter = request.args.get("filter", "all")
    sort_by = request.args.get("sort", "newest")
    tasks = DatabaseManager.list_tasks(search=search, filter_name=active_filter, sort_by=sort_by)
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    try:
        task = DatabaseManager.add_task(request.get_json(silent=True) or {})
        return jsonify(task), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int):
    try:
        task = DatabaseManager.update_task(task_id, request.get_json(silent=True) or {})
        return jsonify(task)
    except KeyError:
        return jsonify({"error": "Task not found."}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int):
    try:
        DatabaseManager.delete_task(task_id)
        return jsonify({"success": True})
    except KeyError:
        return jsonify({"error": "Task not found."}), 404


@app.route("/api/tasks/clear-completed", methods=["DELETE"])
def clear_completed():
    DatabaseManager.delete_completed_tasks()
    return jsonify({"success": True})


@app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id: int):
    try:
        task = DatabaseManager.complete_task(task_id)
        return jsonify(task)
    except KeyError:
        return jsonify({"error": "Task not found."}), 404


@app.route("/api/tasks/<int:task_id>/restore", methods=["POST"])
def restore_task(task_id: int):
    try:
        task = DatabaseManager.restore_task(task_id)
        return jsonify(task)
    except KeyError:
        return jsonify({"error": "Task not found."}), 404


@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(DatabaseManager.list_categories())


@app.route("/api/categories", methods=["POST"])
def create_category():
    payload = request.get_json(silent=True) or {}
    try:
        category = DatabaseManager.create_category(payload.get("name"))
        return jsonify(category), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id: int):
    try:
        category = DatabaseManager.delete_category(category_id)
        return jsonify(category)
    except KeyError:
        return jsonify({"error": "Category not found."}), 404


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(DatabaseManager.get_settings())


@app.route("/api/settings", methods=["PUT"])
def save_settings():
    payload = request.get_json(silent=True) or {}
    settings = DatabaseManager.save_settings(payload.get("theme"), payload.get("accent_color"))
    return jsonify(settings)


@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    return jsonify(DatabaseManager.get_statistics())


@app.route("/api/insights", methods=["GET"])
def get_insights():
    return jsonify(DatabaseManager.get_insights())


@app.route("/api/achievements", methods=["GET"])
def get_achievements():
    return jsonify(DatabaseManager.get_achievements())


@app.route("/api/tasks/export", methods=["GET"])
def export_tasks():
    return jsonify(DatabaseManager.export_tasks())


@app.route("/api/tasks/import", methods=["POST"])
def import_tasks():
    payload = request.get_json(silent=True) or {}
    try:
        imported_ids = DatabaseManager.import_tasks(payload.get("tasks", []))
        return jsonify({"success": True, "inserted_ids": imported_ids}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    DatabaseManager.init_db()
    app.run(host="0.0.0.0", port=5002, debug=True)
