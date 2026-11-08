import argparse
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "expense.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            comment TEXT,
            date TEXT NOT NULL
        )
    """)
    return conn


def add_expense(conn, amount, category, comment):
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO expenses (amount, category, comment, date) VALUES (?, ?, ?, ?)",
        (amount, category, comment, today),
    )
    conn.commit()
    print(f"Добавлено: {amount} | {category} | {comment} | {today}")


def delete_expense(conn, expense_id):
    cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    if cur.rowcount == 0:
        print(f"Траты с номером {expense_id} нет")
    else:
        print(f"Удалена трата №{expense_id}")


def show_list(conn):
    rows = conn.execute(
        "SELECT id, date, amount, category, comment FROM expenses ORDER BY date"
    ).fetchall()
    if not rows:
        print("Трат пока нет")
        return
    for id_, day, amount, category, comment in rows:
        print(f"{id_:>3} | {day} | {amount:>9.2f} | {category:<12} | {comment}")


def build_parser():
    parser = argparse.ArgumentParser(description="Трекер расходов")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="добавить трату")
    add_p.add_argument("amount", type=float, help="сумма")
    add_p.add_argument("category", help="категория")
    add_p.add_argument("comment", nargs="?", default="", help="комментарий")

    sub.add_parser("list", help="показать все траты")

    del_p = sub.add_parser("delete", help="удалить трату")
    del_p.add_argument("id", type=int, help="номер траты")

    return parser


def main():
    args = build_parser().parse_args()
    conn = get_connection()
    try:
        if args.command == "add":
            if args.amount <= 0:
                print("Сумма должна быть больше нуля")
                return
            add_expense(conn, args.amount, args.category, args.comment)
        elif args.command == "list":
            show_list(conn)
        elif args.command == "delete":
            delete_expense(conn, args.id)
    finally:
        conn.close()


if __name__ == "__main__":
    main()