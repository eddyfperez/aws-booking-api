from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier

import pytest

import database
from app import app, BUSINESS_TIMEZONE


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Cada prueba utiliza su propia base de datos temporal.
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
    tomorrow = (
        datetime.now(BUSINESS_TIMEZONE)
        + timedelta(days=1)
    )

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

    # Todos los horarios deben estar disponibles al comenzar.
    initial = client.get(url)

    assert initial.status_code == 200
    assert initial.get_json() == {
        "date": selected_date,
        "available_times": ["09:00", "13:00", "17:00"]
    }

    # Reservar el turno de las 09:00.
    created = client.post(
        "/bookings",
        json=booking_data
    )

    assert created.status_code == 201

    booking_id = created.get_json()["id"]

    # El horario reservado ya no debe aparecer.
    after_booking = client.get(url)

    assert after_booking.status_code == 200
    assert after_booking.get_json()["available_times"] == [
        "13:00", "17:00"
    ]

    # Cancelar la reserva.
    cancelled = client.delete(
        f"/bookings/{booking_id}"
    )

    assert cancelled.status_code == 200

    # El turno debe volver a estar disponible.
    after_cancellation = client.get(url)

    assert after_cancellation.status_code == 200
    assert after_cancellation.get_json()["available_times"] == [
        "09:00", "13:00", "17:00"
    ]


def test_simultaneous_bookings(client, booking_data):
    barrier = Barrier(2)

    def send_booking():
        # Cada tarea utiliza un cliente independiente.
        with app.test_client() as separate_client:
            barrier.wait(timeout=5)

            response = separate_client.post(
                "/bookings",
                json=booking_data
            )

            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(send_booking)
        second = executor.submit(send_booking)

        results = [
            first.result(timeout=10),
            second.result(timeout=10)
        ]

    # Una solicitud tiene éxito y la otra encuentra un conflicto.
    assert sorted(results) == [201, 409]

    listing = client.get("/bookings")

    assert listing.status_code == 200
    assert len(listing.get_json()["bookings"]) == 1


def test_availability_uses_business_timezone(client, monkeypatch):
    import app as app_module
    from datetime import timezone

    # Momento fijo: 14:00 UTC = 10:00 en Santo Domingo.
    fixed_now = datetime(
        2030, 6, 15, 14, 0,
        tzinfo=timezone.utc
    )

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                # Simular un servidor cuya hora local sea UTC.
                return fixed_now.replace(tzinfo=None)

            return fixed_now.astimezone(tz)

    # Cambiar el reloj de la aplicación solo durante esta prueba.
    monkeypatch.setattr(
        app_module,
        "datetime",
        FixedDatetime
    )

    response = client.get(
        "/availability?date=2030-06-15"
    )

    assert response.status_code == 200
    assert response.get_json()["available_times"] == [
        "13:00", "17:00"
    ]

    # Las 13:00 siguen siendo futuras en Santo Domingo.
    created = client.post("/bookings", json={
        "customer_name": "Prueba de zona horaria",
        "date": "2030-06-15",
        "time": "13:00"
    })

    assert created.status_code == 201