# AWS Booking API

A booking REST API built with Python and Flask as the first stage
of a serverless AWS portfolio project.

## Current features

- Create and list bookings.
- Cancel bookings by ID.
- Validate required fields and future appointment dates.
- Restrict appointments to 09:00, 13:00, and 17:00.
- Reject duplicate bookings for the same date and time.
- Release a time slot when its booking is cancelled.
- Six automated tests using pytest.

## Technologies

Python 3.12, Flask, pytest, and Git.

## Run locally on Windows

```powershell
git clone https://github.com/eddyfperez/aws-booking-api.git
cd aws-booking-api
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

The development API runs at http://127.0.0.1:5000.

## Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /health | Check API status |
| POST | /bookings | Create a booking |
| GET | /bookings | List bookings |
| DELETE | /bookings/<booking_id> | Cancel a booking |

Example booking request:

```json
{
  "customer_name": "Example Customer",
  "date": "2099-12-15",
  "time": "09:00"
}
```

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

## Current limitations

- Bookings are stored in memory and disappear when the app restarts.
- Scheduling assumes one cleaning team and uses the computer's local time.
- Duplicate checks do not yet protect against simultaneous requests.
- Authentication is not implemented.
- The application has not been deployed to AWS.

## Planned improvements

- Persistent storage with DynamoDB.
- Atomic booking conflict protection.
- Deployment with AWS Lambda and API Gateway.
- Customer authentication with Amazon Cognito.
- Automated testing through GitHub Actions.