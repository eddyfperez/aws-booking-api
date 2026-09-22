# AWS Booking API

A booking REST API built with Python and Flask as part of a
cloud engineering portfolio project.

The current version runs locally or in Docker, stores bookings
in SQLite, and runs automated tests through GitHub Actions.
AWS deployment is a planned next stage.

## Features

- Create, list, and cancel bookings.
- Validate required fields and future appointment dates.
- Support fixed appointment times: 09:00, 13:00, and 17:00.
- Prevent duplicate bookings using a database uniqueness constraint.
- Check available time slots for a selected date.
- Release time slots when bookings are cancelled.
- Persist bookings across application restarts.
- Interpret appointments in the America/Santo_Domingo timezone.
- Run nine automated tests, including concurrency and timezone tests.
- Run in Docker with Gunicorn and persistent storage.

## Technologies

- Python 3.12
- Flask
- SQLite
- pytest
- Git and GitHub
- GitHub Actions
- Docker
- Gunicorn

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | API endpoints, validation, and scheduling rules |
| `database.py` | SQLite initialization and database operations |
| `test/test_bookings.py` | Automated tests |
| `requirements.txt` | Python dependencies |
| `requirements-docker.txt` | Dependencies for the Docker runtime |
| `Dockerfile` | Container image definition |
| `.dockerignore` | Files excluded from the Docker build context |
| `.gitignore` | Files excluded from Git tracking |
| `.github/workflows/tests.yml` | Automated Python testing workflow |

## Run locally on Windows

### Prerequisites

- Python 3.12
- Git

### Setup

```powershell
git clone https://github.com/eddyfperez/aws-booking-api.git
cd aws-booking-api
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Start the development server

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

The API runs at:

```text
http://127.0.0.1:5000
```

Check its status at:

```text
http://127.0.0.1:5000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Debug mode is for local development only.

## Run with Docker

### Prerequisites

- Docker Desktop installed and running
- WSL 2 when using the Windows WSL backend

Run the following commands from the project root.

### Build the image

```powershell
docker build -t booking-api:local .
```

### Create and start the container

```powershell
docker run -d --name booking-api -p 127.0.0.1:5001:5000 --mount source=booking-data,target=/app/data booking-api:local
```

The containerized API runs at:

```text
http://127.0.0.1:5001
```

Check its status at:

```text
http://127.0.0.1:5001/health
```

The container runs Gunicorn as a non-root user. Its published
port is bound to the local computer.

### Stop and start the existing container

```powershell
docker stop booking-api
docker start booking-api
```

Use `docker start` for an existing stopped container.
Use `docker run` to create a new container.

### View logs

```powershell
docker logs booking-api
```

### Rebuild after code changes

```powershell
docker build -t booking-api:local .
docker stop booking-api
docker rm booking-api
docker run -d --name booking-api -p 127.0.0.1:5001:5000 --mount source=booking-data,target=/app/data booking-api:local
```

Reusing the same volume preserves the Docker database.

## API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Check API status |
| POST | `/bookings` | Create a booking |
| GET | `/bookings` | List bookings |
| DELETE | `/bookings/<booking_id>` | Cancel a booking |
| GET | `/availability?date=YYYY-MM-DD` | List available time slots |

## Booking rules

- Scheduling assumes one cleaning team.
- Appointments start at 09:00, 13:00, or 17:00.
- Each slot represents a fixed three-hour appointment.
- Only one booking is allowed per date and time slot.
- Appointment dates and times must be in the future.
- All appointment times use America/Santo_Domingo.
- Customer name, date, and time are required.
- Cancellation deletes the booking and releases its slot.

Availability is informational. A slot is reserved only when
the booking is successfully saved.

## Example requests

These PowerShell examples target Docker on port 5001.
For the local Flask server, change the base URL to port 5000.

### Create a booking

Use a future date when running this example.

```powershell
$baseUrl = "http://127.0.0.1:5001"

$body = @{
    customer_name = "Example Customer"
    date = "2099-12-15"
    time = "09:00"
} | ConvertTo-Json

$booking = Invoke-RestMethod `
    -Uri "$baseUrl/bookings" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$booking
```

A successful request returns HTTP 201 and the created booking:

```json
{
  "id": "<generated-uuid>",
  "customer_name": "Example Customer",
  "date": "2099-12-15",
  "time": "09:00",
  "status": "confirmed"
}
```

### List bookings

```powershell
Invoke-RestMethod `
    -Uri "$baseUrl/bookings" `
    -Method Get | ConvertTo-Json -Depth 5
```

### Check availability

```powershell
Invoke-RestMethod `
    -Uri "$baseUrl/availability?date=2099-12-15" `
    -Method Get | ConvertTo-Json
```

If only the 09:00 slot is booked, the response is:

```json
{
  "date": "2099-12-15",
  "available_times": ["13:00", "17:00"]
}
```

### Cancel the booking

Run this in the same PowerShell session where `$booking`
was assigned:

```powershell
Invoke-RestMethod `
    -Uri "$baseUrl/bookings/$($booking.id)" `
    -Method Delete
```

## Response codes

| Code | Meaning |
|------|---------|
| 200 | Successful query or cancellation |
| 201 | Booking created |
| 400 | Invalid or incomplete request |
| 404 | Booking not found |
| 409 | Date and time slot already booked |

## Data storage

The application creates the SQLite table automatically.

By default, local execution stores data in `bookings.db`
beside `database.py`. The `DATABASE_PATH` environment variable
can override this location.

In Docker:

- Database path: `/app/data/bookings.db`
- Named volume: `booking-data`

The Docker database is separate from the local Windows database.
Existing Windows bookings are not copied into the image.

The named volume survives container removal. Deleting the volume
also deletes its stored data.

Database files are excluded from Git and the Docker build context.

## Automated tests

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The suite includes nine tests:

1. Create and list a booking.
2. Reject a booking without a customer name.
3. Reject duplicate bookings.
4. Reject unavailable appointment times.
5. Cancel a booking and reserve the released slot.
6. Return 404 when cancelling an unknown booking.
7. Update availability after booking and cancellation.
8. Handle two simultaneous requests for the same slot.
9. Apply the business timezone when checking availability
   and creating a booking.

Each test uses a separate temporary SQLite database.
Test booking operations do not modify manually created bookings.

The concurrency test expects one successful booking, one
conflict response, and exactly one stored reservation.
It is not a full load test.

## Continuous integration

GitHub Actions runs the Python tests on pushes to `main`
and pull requests targeting `main`.

The workflow:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Installs dependencies.
4. Runs pytest.

The current workflow does not build or test the Docker image.

## Manual verification

The following scenarios have been checked manually:

- Bookings remain available after restarting Flask.
- The Docker API responds through its published port.
- A booking remains available after removing and recreating
  the container with the same named volume.

## Current limitations

- The API does not implement authentication or authorization.
- Scheduling supports one cleaning team and one business timezone.
- Service types, variable durations, and customer addresses
  are not implemented.
- Bookings cannot yet be rescheduled.
- Cancelled bookings are deleted without retaining history.
- Listing bookings has no pagination.
- Availability reads all bookings before filtering by date.
- High-load behavior has not been tested.
- Persistent storage has no automated backup process.
- The application has not been deployed to AWS.

This is a learning project and is not ready for real customer use.

## Roadmap

- Build and smoke-test the Docker image in GitHub Actions.
- Add authentication and customer-specific access controls.
- Implement booking rescheduling.
- Add service selection and multiple cleaning teams.
- Implement a DynamoDB storage backend.
- Adapt the application for AWS Lambda and API Gateway.
- Define AWS infrastructure as code.
- Automate deployment using GitHub Actions and OIDC.
- Add monitoring, operational alerts, and backup procedures.