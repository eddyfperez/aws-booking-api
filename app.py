import sqlite3
from datetime import datetime
from uuid import uuid4

from flask import Flask, request

from database import (
    init_db,
    insert_booking,
    get_bookings,
    delete_booking
)

app = Flask(__name__)

# Crear la tabla si todavía no existe.
init_db()

# Horarios para un solo equipo de limpieza.
AVAILABLE_TIMES = ["09:00", "13:00", "17:00"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/bookings")
def create_booking():
    data = request.get_json(silent=True)

    # Comprobar que el cliente envió un objeto JSON.
    if not isinstance(data, dict):
        return {
            "error": "Debes enviar un objeto JSON válido"
        }, 400

    # Comprobar los campos obligatorios.
    required_fields = ["customer_name", "date", "time"]

    for field in required_fields:
        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            return {
                "error": f"El campo {field} es obligatorio"
            }, 400

    # Convertir el texto recibido en una fecha y hora.
    date_text = data["date"].strip()
    time_text = data["time"].strip()

    try:
        appointment = datetime.strptime(
            f"{date_text} {time_text}",
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        return {
            "error": "Fecha u hora inválida. Usa YYYY-MM-DD y HH:MM"
        }, 400

    # Por ahora usamos la hora local de la computadora.
    if appointment <= datetime.now():
        return {
            "error": "La reserva debe ser para una fecha y hora futura"
        }, 400

    # Usar un formato uniforme para guardar los datos.
    normalized_date = appointment.strftime("%Y-%m-%d")
    normalized_time = appointment.strftime("%H:%M")

    # Comprobar que el horario esté permitido.
    if normalized_time not in AVAILABLE_TIMES:
        return {
            "error": "Horario no disponible",
            "available_times": AVAILABLE_TIMES
        }, 400

    # Preparar la reserva.
    booking = {
        "id": str(uuid4()),
        "customer_name": data["customer_name"].strip(),
        "date": normalized_date,
        "time": normalized_time,
        "status": "confirmed"
    }

    # SQLite impide guardar dos reservas para el mismo turno.
    try:
        insert_booking(booking)
    except sqlite3.IntegrityError as error:
        if "bookings.date, bookings.time" in str(error):
            return {
                "error": "Ya existe una reserva para esa fecha y hora"
            }, 409

        # No tratar otros errores de integridad como duplicados.
        raise

    return booking, 201


@app.get("/bookings")
def list_bookings():
    return {"bookings": get_bookings()}, 200


@app.delete("/bookings/<booking_id>")
def cancel_booking(booking_id):
    deleted = delete_booking(booking_id)

    if not deleted:
        return {
            "error": "Reserva no encontrada"
        }, 404

    return {
        "message": "Reserva cancelada correctamente",
        "id": booking_id,
        "status": "cancelled"
    }, 200

@app.get("/availability")
def get_availability():
    date_text = request.args.get("date", "").strip()

    try:
        selected_date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return {
            "error": "Debes indicar una fecha válida con formato YYYY-MM-DD"
        }, 400

    now = datetime.now()

    if selected_date < now.date():
        return {
            "error": "No puedes consultar una fecha pasada"
        }, 400

    normalized_date = selected_date.strftime("%Y-%m-%d")

    # Buscar los horarios que ya están reservados ese día.
    occupied_times = {
        booking["time"]
        for booking in get_bookings()
        if booking["date"] == normalized_date
    }

    available_times = []

    for time in AVAILABLE_TIMES:
        appointment = datetime.strptime(
            f"{normalized_date} {time}",
            "%Y-%m-%d %H:%M"
        )

        if time not in occupied_times and appointment > now:
            available_times.append(time)

    return {
        "date": normalized_date,
        "available_times": available_times
    }, 200