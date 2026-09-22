import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "bookings.db"


def init_db():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(date, time)
            )
        """)

        connection.commit()
    finally:
        connection.close()


def insert_booking(booking):
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            INSERT INTO bookings (
                id, customer_name, date, time, status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            booking["id"],
            booking["customer_name"],
            booking["date"],
            booking["time"],
            booking["status"]
        ))

        connection.commit()
    finally:
        connection.close()


def get_bookings():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute("""
            SELECT id, customer_name, date, time, status
            FROM bookings
            ORDER BY date, time
        """).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


def delete_booking(booking_id):
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = connection.execute(
            "DELETE FROM bookings WHERE id = ?",
            (booking_id,)
        )

        connection.commit()

        return cursor.rowcount > 0
    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("Base de datos creada correctamente.")