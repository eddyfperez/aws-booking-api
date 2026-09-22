from datetime import datetime, timedelta

import pytest

import database
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Usar una base temporal distinta en cada prueba.
    test_database = tmp_path / "test_bookings.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database
    )

    database.init_db()
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def booking_data():
    tomorrow = datetime.now() + timedelta(days=1)

    return {
        "customer_name": "Cliente de prueba",
        "date": tomorrow.strftime("%Y-%m-%d"),
        "time": "09:00"
    }


def test_create_booking(client, booking_data):
    response = client.post(
        "/bookings",
        json=booking_data
    )

    assert response.status_code == 201

    created = response.get_json()

    assert created["customer_name"] == "Cliente de prueba"
    assert created["status"] == "confirmed"
    assert "id" in created

    listing = client.get("/bookings")

    assert listing.status_code == 200
    assert listing.get_json()["bookings"] == [created]


def test_missing_customer_name(client, booking_data):
    del booking_data["customer_name"]

    response = client.post(
        "/bookings",
        json=booking_data
    )

    assert response.status_code == 400
    assert client.get("/bookings").get_json()["bookings"] == []


def test_duplicate_booking(client, booking_data):
    first = client.post(
        "/bookings",
        json=booking_data
    )

    second = client.post(
        "/bookings",
        json=booking_data
    )

    assert first.status_code == 201
    assert second.status_code == 409

    saved = client.get("/bookings").get_json()["bookings"]

    assert len(saved) == 1


def test_unavailable_time(client, booking_data):
    booking_data["time"] = "10:00"

    response = client.post(
        "/bookings",
        json=booking_data
    )

    assert response.status_code == 400
    assert client.get("/bookings").get_json()["bookings"] == []


def test_cancel_and_rebook(client, booking_data):
    created = client.post(
        "/bookings",
        json=booking_data
    )

    assert created.status_code == 201

    booking_id = created.get_json()["id"]

    cancelled = client.delete(
        f"/bookings/{booking_id}"
    )

    assert cancelled.status_code == 200
    assert client.get("/bookings").get_json()["bookings"] == []

    new_booking = client.post(
        "/bookings",
        json=booking_data
    )

    assert new_booking.status_code == 201


def test_cancel_unknown_booking(client):
    response = client.delete(
        "/bookings/id-inexistente"
    )

    assert response.status_code == 404


def test_availability_updates_after_booking_and_cancellation(
    client, booking_data
):
    selected_date = booking_data["date"]
    url = f"/availability?date={selected_date}"

    # Al comenzar, todos los horarios deben estar disponibles.
    initial = client.get(url)

    assert initial.status_code == 200
    assert initial.get_json() == {
        "date": selected_date,
        "available_times": ["09:00", "13:00", "17:00"]
    }

    # Reservar el turno de las 09:00.
    created = client.post("/bookings", json=booking_data)

    assert created.status_code == 201

    booking_id = created.get_json()["id"]

    # El horario reservado ya no debe aparecer.
    after_booking = client.get(url)

    assert after_booking.status_code == 200
    assert after_booking.get_json()["available_times"] == [
        "13:00", "17:00"
    ]

    # Cancelar la reserva.
    cancelled = client.delete(f"/bookings/{booking_id}")

    assert cancelled.status_code == 200

    # El turno debe volver a estar disponible.
    after_cancellation = client.get(url)

    assert after_cancellation.status_code == 200
    assert after_cancellation.get_json()["available_times"] == [
        "09:00", "13:00", "17:00"
    ]
