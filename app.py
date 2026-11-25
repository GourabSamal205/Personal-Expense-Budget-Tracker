import sqlite3
from pathlib import Path
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
DB_PATH = Path(__file__).parent / "expenses.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL CHECK (monthly_limit > 0)
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                spent_date TEXT NOT NULL,
                FOREIGN KEY (category) REFERENCES budgets(category)
            );

            INSERT OR IGNORE INTO budgets (category, monthly_limit) VALUES
                ('Food', 3000),
                ('Travel', 1500),
                ('Books', 2000),
                ('Bills', 2500);
            """
        )


init_db()


@app.route("/")
def index():
    with get_connection() as conn:
        expenses = conn.execute(
            "SELECT * FROM expenses ORDER BY spent_date DESC, id DESC"
        ).fetchall()

        category_summary = conn.execute(
            """
            SELECT
                b.category,
                b.monthly_limit,
                COALESCE(SUM(e.amount), 0) AS total_spent
            FROM budgets b
            LEFT JOIN expenses e ON b.category = e.category
            GROUP BY b.category, b.monthly_limit
            ORDER BY total_spent DESC
            """
        ).fetchall()

        grand_total = sum(row["total_spent"] for row in category_summary)

    return render_template(
        "index.html",
        expenses=expenses,
        category_summary=category_summary,
        grand_total=grand_total,
    )


@app.post("/add")
def add_expense():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    amount = request.form.get("amount", type=float)
    spent_date = request.form.get("spent_date", "").strip()

    if title and category and amount and amount > 0 and spent_date:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO expenses (title, category, amount, spent_date)
                VALUES (?, ?, ?, ?)
                """,
                (title, category, amount, spent_date),
            )

    return redirect(url_for("index"))


@app.post("/delete/<int:expense_id>")
def delete_expense(expense_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)