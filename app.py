from flask import Flask, request
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)

# Almacenamiento temporal: se vacía al reiniciar la aplicación.
bookings = []

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

    # Guardar y comparar las fechas con un formato uniforme.
    normalized_date = appointment.strftime("%Y-%m-%d")
    normalized_time = appointment.strftime("%H:%M")

    # Comprobar que el horario esté permitido.
    if normalized_time not in AVAILABLE_TIMES:
        return {
            "error": "Horario no disponible",
            "available_times": AVAILABLE_TIMES
        }, 400

    # Comprobar si el turno ya está ocupado.
    for existing_booking in bookings:
        if (
            existing_booking["date"] == normalized_date
            and existing_booking["time"] == normalized_time
        ):
            return {
                "error": "Ya existe una reserva para esa fecha y hora"
            }, 409

    # Crear y guardar la reserva.
    booking = {
        "id": str(uuid4()),
        "customer_name": data["customer_name"].strip(),
        "date": normalized_date,
        "time": normalized_time,
        "status": "confirmed"
    }

    bookings.append(booking)

    return booking, 201


@app.get("/bookings")
def list_bookings():
    return {"bookings": bookings}, 200

@app.delete("/bookings/<booking_id>")
def cancel_booking(booking_id):
    for index, booking in enumerate(bookings):
        if booking["id"] == booking_id:
            cancelled_booking = bookings.pop(index)

            return {
                "message": "Reserva cancelada correctamente",
                "id": cancelled_booking["id"],
                "status": "cancelled"
            }, 200

    return {
        "error": "Reserva no encontrada"
    }, 404