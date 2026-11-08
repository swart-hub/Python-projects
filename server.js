const express = require("express");
const Database = require("better-sqlite3");
const path = require("path");

const app = express();
const db = new Database("education-center.db");

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

db.pragma("foreign_keys = ON");

db.exec(`
  CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    group_name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    monthly_fee INTEGER NOT NULL DEFAULT 0,
    next_due_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    period_month TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(student_id, period_month)
  );
`);

function dateOffset(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function seedDatabase() {
  const count = db.prepare("SELECT COUNT(*) AS count FROM students").get().count;
  if (count > 0) return;

  const students = [
    ["Алиса Воронова", "Английский · A2", "+7 900 123-45-67", 6500, dateOffset(-8)],
    ["Максим Орлов", "Математика · 8 класс", "+7 900 234-56-78", 7200, dateOffset(-2)],
    ["София Белова", "Английский · B1", "+7 900 345-67-89", 6500, dateOffset(0)],
    ["Марк Соколов", "Программирование", "+7 900 456-78-90", 8900, dateOffset(3)],
    ["Ева Кузнецова", "Подготовка к школе", "+7 900 567-89-01", 5800, dateOffset(6)],
    ["Артём Попов", "Математика · 9 класс", "+7 900 678-90-12", 7200, dateOffset(12)],
    ["Мия Лебедева", "Английский · A1", "+7 900 789-01-23", 6500, dateOffset(18)],
    ["Даниил Смирнов", "Программирование", "+7 900 890-12-34", 8900, dateOffset(25)]
  ];

  const insert = db.prepare(`
    INSERT INTO students (name, group_name, phone, monthly_fee, next_due_date)
    VALUES (?, ?, ?, ?, ?)
  `);

  const addStudents = db.transaction((rows) => {
    rows.forEach((row) => insert.run(...row));
  });

  addStudents(students);

  const currentPeriod = new Date().toISOString().slice(0, 7);
  const today = new Date().toISOString().slice(0, 10);

  db.prepare(`
    INSERT INTO payments (student_id, amount, payment_date, period_month)
    VALUES (?, ?, ?, ?)
  `).run(1, 6500, today, currentPeriod);
}

seedDatabase();

function getStudentStatus(dueDate) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const due = new Date(`${dueDate}T00:00:00`);
  const daysLeft = Math.ceil((due - today) / 86400000);

  if (daysLeft < 0) return "overdue";
  if (daysLeft <= 7) return "soon";
  return "good";
}

app.get("/api/dashboard", (req, res) => {
  const students = db.prepare(`
    SELECT s.*,
      COALESCE((
        SELECT SUM(p.amount)
        FROM payments p
        WHERE p.student_id = s.id
          AND p.period_month = ?
      ), 0) AS paid_this_month
    FROM students s
    ORDER BY s.name
  `).all(new Date().toISOString().slice(0, 7));

  const payments = db.prepare(`
    SELECT p.*, s.name AS student_name, s.group_name
    FROM payments p
    JOIN students s ON s.id = p.student_id
    ORDER BY p.payment_date DESC, p.id DESC
    LIMIT 8
  `).all();

  const totalStudents = students.length;
  const overdueStudents = students.filter(
    (student) => getStudentStatus(student.next_due_date) === "overdue"
  ).length;

  const dueSoonStudents = students.filter(
    (student) => getStudentStatus(student.next_due_date) === "soon"
  ).length;

  const expectedRevenue = students.reduce(
    (sum, student) => sum + student.monthly_fee,
    0
  );

  const collectedRevenue = students.reduce(
    (sum, student) => sum + student.paid_this_month,
    0
  );

  res.json({
    students,
    payments,
    stats: {
      totalStudents,
      overdueStudents,
      dueSoonStudents,
      expectedRevenue,
      collectedRevenue
    }
  });
});

app.get("/api/students", (req, res) => {
  const students = db.prepare(`
    SELECT * FROM students ORDER BY name
  `).all();

  res.json(students);
});

app.post("/api/students", (req, res) => {
  const { name, group_name, phone, monthly_fee, next_due_date } = req.body;

  if (!name || !group_name || !next_due_date || Number(monthly_fee) < 0) {
    return res.status(400).json({ error: "Заполните обязательные поля" });
  }

  const result = db.prepare(`
    INSERT INTO students (name, group_name, phone, monthly_fee, next_due_date)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    name.trim(),
    group_name.trim(),
    (phone || "").trim(),
    Number(monthly_fee),
    next_due_date
  );

  res.status(201).json({ id: result.lastInsertRowid });
});

app.get("/api/payments", (req, res) => {
  const payments = db.prepare(`
    SELECT p.*, s.name AS student_name, s.group_name
    FROM payments p
    JOIN students s ON s.id = p.student_id
    ORDER BY p.payment_date DESC, p.id DESC
  `).all();

  res.json(payments);
});

function nextMonthDueDate(periodMonth, dueDay) {
  const [year, month] = periodMonth.split("-").map(Number);
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const lastDay = new Date(nextYear, nextMonth, 0).getDate();
  const day = Math.min(dueDay, lastDay);

  return `${nextYear}-${String(nextMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

app.post("/api/payments", (req, res) => {
  const { student_id, amount, payment_date, period_month } = req.body;

  if (!student_id || !amount || !payment_date || !period_month) {
    return res.status(400).json({ error: "Заполните все поля оплаты" });
  }

  const student = db.prepare("SELECT * FROM students WHERE id = ?").get(student_id);

  if (!student) {
    return res.status(404).json({ error: "Ученик не найден" });
  }

  try {
    const insertPayment = db.prepare(`
      INSERT INTO payments (student_id, amount, payment_date, period_month)
      VALUES (?, ?, ?, ?)
    `);

    insertPayment.run(
      Number(student_id),
      Number(amount),
      payment_date,
      period_month
    );

    const dueDay = Number(student.next_due_date.slice(8, 10));
    const newDueDate = nextMonthDueDate(period_month, dueDay);

    if (newDueDate > student.next_due_date) {
      db.prepare(`
        UPDATE students SET next_due_date = ? WHERE id = ?
      `).run(newDueDate, student_id);
    }

    res.status(201).json({ success: true });
  } catch (error) {
    if (String(error).includes("UNIQUE")) {
      return res.status(409).json({
        error: "Оплата за этот месяц уже зарегистрирована"
      });
    }

    res.status(500).json({ error: "Не удалось сохранить оплату" });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Сайт запущен: http://localhost:${PORT}`);
});