import sqlite3
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

# База лежит рядом с этим файлом. Если хочешь свою старую базу,
# замени на Path("database/expense.db")
DB_PATH = Path(__file__).parent / "expense.db"
CATEGORIES = ["еда", "транспорт", "жильё", "развлечения", "здоровье", "другое"]

STYLE = """
QWidget {
    background: #15181d;
    color: #e6e8eb;
    font-family: "Segoe UI";
    font-size: 14px;
}
#panel {
    background: #1c2026;
    border-radius: 14px;
}
#title { font-size: 22px; font-weight: 600; background: transparent; }
#hint, #status { color: #8b939e; background: transparent; }
#total {
    background: #1c2026;
    border-radius: 14px;
    padding: 16px 20px;
    font-size: 26px;
    font-weight: 600;
    color: #f2b84b;
}
QLabel { background: transparent; }
QLineEdit, QComboBox {
    background: #15181d;
    border: 1px solid #2c333c;
    border-radius: 8px;
    padding: 9px 10px;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #f2b84b; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #1c2026;
    border: 1px solid #2c333c;
    selection-background-color: #2c333c;
}
QPushButton {
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}
#addButton { background: #f2b84b; color: #15181d; }
#addButton:hover { background: #ffc962; }
#deleteButton {
    background: transparent;
    border: 1px solid #5a2f35;
    color: #ff8a93;
}
#deleteButton:hover { background: #3a2226; }
QTableWidget {
    background: #1c2026;
    border: none;
    border-radius: 14px;
    gridline-color: transparent;
    selection-background-color: #2c333c;
    selection-color: #ffffff;
    outline: none;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #242a32; }
QHeaderView::section {
    background: #1c2026;
    color: #8b939e;
    border: none;
    border-bottom: 1px solid #2c333c;
    padding: 8px;
    font-weight: 500;
}
"""


# ---------- работа с базой ----------
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


def add_expense(amount, category, comment):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO expenses (amount, category, comment, date) VALUES (?, ?, ?, ?)",
            (amount, category, comment, date.today().isoformat()),
        )


def delete_expense(expense_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))


def get_expenses():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, date, amount, category, comment FROM expenses ORDER BY id DESC"
        ).fetchall()


# ---------- окно ----------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Трекер расходов")
        self.resize(980, 600)
        self.setStyleSheet(STYLE)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # левая панель: форма
        panel = QWidget()
        panel.setObjectName("panel")
        panel.setFixedWidth(300)
        form = QVBoxLayout(panel)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(10)

        title = QLabel("Новая трата")
        title.setObjectName("title")
        form.addWidget(title)
        form.addSpacing(6)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма")
        self.category_box = QComboBox()
        self.category_box.setEditable(True)
        self.category_box.addItems(CATEGORIES)
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Комментарий (необязательно)")
        self.add_button = QPushButton("Добавить трату")
        self.add_button.setObjectName("addButton")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)

        form.addWidget(self.amount_input)
        form.addWidget(self.category_box)
        form.addWidget(self.comment_input)
        form.addSpacing(4)
        form.addWidget(self.add_button)
        form.addWidget(self.status)
        form.addStretch()

        # правая часть: итог и таблица
        right = QVBoxLayout()
        right.setSpacing(14)

        self.total_label = QLabel("")
        self.total_label.setObjectName("total")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["№", "Дата", "Сумма", "Категория", "Комментарий"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setHighlightSections(False)

        self.delete_button = QPushButton("Удалить выбранную")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.setCursor(Qt.PointingHandCursor)

        right.addWidget(self.total_label)
        right.addWidget(self.table)
        right.addWidget(self.delete_button, alignment=Qt.AlignRight)

        root.addWidget(panel)
        root.addLayout(right, 1)

        # сигналы: «по событию вызови функцию»
        self.add_button.clicked.connect(self.on_add)
        self.amount_input.returnPressed.connect(self.on_add)
        self.comment_input.returnPressed.connect(self.on_add)
        self.delete_button.clicked.connect(self.on_delete)

    def set_status(self, text, error=False):
        color = "#ff8a93" if error else "#8bd5a0"
        self.status.setStyleSheet(f"color: {color}; background: transparent;")
        self.status.setText(text)

    def on_add(self):
        raw = self.amount_input.text().strip().replace(",", ".")
        try:
            amount = float(raw)
        except ValueError:
            self.set_status("Введи сумму числом, например 450", error=True)
            return
        if amount <= 0:
            self.set_status("Сумма должна быть больше нуля", error=True)
            return
        category = self.category_box.currentText().strip() or "другое"
        add_expense(amount, category, self.comment_input.text().strip())
        self.amount_input.clear()
        self.comment_input.clear()
        self.amount_input.setFocus()
        self.set_status("Трата добавлена")
        self.refresh()

    def on_delete(self):
        row = self.table.currentRow()
        if row < 0:
            self.set_status("Сначала выбери трату в таблице", error=True)
            return
        expense_id = int(self.table.item(row, 0).text())
        delete_expense(expense_id)
        self.set_status(f"Удалена трата №{expense_id}")
        self.refresh()

    def refresh(self):
        rows = get_expenses()
        self.table.setRowCount(len(rows))
        total = 0.0
        for r, (id_, day, amount, category, comment) in enumerate(rows):
            total += amount
            values = [str(id_), day, f"{amount:,.2f}".replace(",", " "), category, comment or ""]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.total_label.setText(f"Всего потрачено: {total:,.2f}".replace(",", " "))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())