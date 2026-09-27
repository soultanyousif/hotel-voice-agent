"""
Mock hotel database for the Najdi voice booking agent demo.
Creates and seeds a small SQLite database with room types and bookings
"""

import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "hotel.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_schema(conn):
    conn.execute("DROP TABLE IF EXISTS bookings")
    conn.execute("DROP TABLE IF EXISTS room_types")

    conn.execute("""
        CREATE TABLE room_types (
            id INTEGER PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_ar TEXT NOT NULL,
            price_per_night INTEGER NOT NULL,
            capacity INTEGER NOT NULL,
            count_available INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type_id INTEGER NOT NULL,
            guest_name TEXT NOT NULL,
            guest_phone TEXT,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            num_guests INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TEXT NOT NULL,
            FOREIGN KEY (room_type_id) REFERENCES room_types (id)
        )
    """)
    conn.commit()


def seed_data(conn):
    room_types = [
        (1, "Standard Room", "غرفة قياسية", 450, 2, 10),
        (2, "Deluxe Room", "غرفة ديلوكس", 650, 2, 8),
        (3, "Executive Suite", "جناح تنفيذي", 1200, 3, 4),
        (4, "Royal Suite", "الجناح الملكي", 2500, 4, 2),
    ]
    conn.executemany(
        """INSERT INTO room_types
           (id, name_en, name_ar, price_per_night, capacity, count_available)
           VALUES (?, ?, ?, ?, ?, ?)""",
        room_types,
    )

    # A few existing bookings so availability checks have something
    sample_bookings = [
        (2, "Somebody1", "0501234567", "2026-10-05", "2026-10-08", 2, "confirmed", "2026-09-20"),
        (2, "Somebody2", "0559876543", "2026-10-06", "2026-10-09", 1, "confirmed", "2026-09-21"),
        (3, "Somebody3", "0538889999", "2026-10-10", "2026-10-12", 2, "confirmed", "2026-09-22"),
    ]
    conn.executemany(
        """INSERT INTO bookings
           (room_type_id, guest_name, guest_phone, check_in, check_out, num_guests, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_bookings,
    )
    conn.commit()


def get_room_types():
    """Return all room types with base price and capacity, no date filtering."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name_en, name_ar, price_per_night, capacity FROM room_types"
    ).fetchall()
    conn.close()
    keys = ["room_type_id", "name_en", "name_ar", "price_per_night", "capacity"]
    return [dict(zip(keys, row)) for row in rows]


def get_available_rooms(check_in, check_out, room_type_id=None):
   
    conn = get_connection()
    query = "SELECT id, name_en, name_ar, price_per_night, capacity, count_available FROM room_types"
    params = []
    if room_type_id is not None:
        query += " WHERE id = ?"
        params.append(room_type_id)
    room_types = conn.execute(query, params).fetchall()

    results = []
    for rt_id, name_en, name_ar, price, capacity, count_available in room_types:
        overlapping = conn.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE room_type_id = ?
            AND status = 'confirmed'
            AND check_in < ?
            AND check_out > ?
            """,
            (rt_id, check_out, check_in),
        ).fetchone()[0]

        remaining = count_available - overlapping
        if remaining > 0:
            results.append({
                "room_type_id": rt_id,
                "name_en": name_en,
                "name_ar": name_ar,
                "price_per_night": price,
                "capacity": capacity,
                "remaining": remaining,
            })

    conn.close()
    return results


def create_booking(room_type_id, guest_name, check_in, check_out, num_guests, guest_phone=None):
    """Create a booking after confirming availability.

    Returns the new booking id, or None if no rooms of that type are
    available for the requested dates.
    """
    if not get_available_rooms(check_in, check_out, room_type_id):
        return None

    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO bookings
        (room_type_id, guest_name, guest_phone, check_in, check_out, num_guests, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """,
        (room_type_id, guest_name, guest_phone, check_in, check_out, num_guests, date.today().isoformat()),
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id


def get_booking(booking_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT id, room_type_id, guest_name, guest_phone, check_in, check_out, num_guests, status
           FROM bookings WHERE id = ?""",
        (booking_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    keys = ["id", "room_type_id", "guest_name", "guest_phone", "check_in", "check_out", "num_guests", "status"]
    return dict(zip(keys, row))


if __name__ == "__main__":
    conn = get_connection()
    create_schema(conn)
    seed_data(conn)
    conn.close()
    print(f"Created and seeded {DB_PATH}")