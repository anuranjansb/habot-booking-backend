# HABOT Booking Backend

A Flask backend prototype for the HABOT LSA Service Booking platform.

The system connects parents with Learning Support Assistants (LSAs), manages booking requests, prevents double-bookings at the database level, and processes payment events through a webhook.

## Features

- Flask REST API
- PostgreSQL database
- SQLAlchemy ORM
- Alembic / Flask-Migrate database migrations
- Docker and Docker Compose support
- JWT-based authentication
- Role-based authorization
- Parent ownership authorization
- LSA availability search
- Booking validation
- Database-level overlapping booking prevention
- Payment webhook processing
- Idempotent payment event handling
- Automated pytest test suite
- GitHub Actions CI
- Swagger UI API documentation

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- SQLAlchemy
- PostgreSQL
- Pytest
- Flask-JWT-Extended
- Docker
- GitHub Actions

---

# Architecture

The application follows a lightweight Flask MVC-style architecture.

```text
Client
   |
   v
Flask Routes
   |
   v
Authentication / Authorization
   |
   v
Services
   |
   v
SQLAlchemy ORM
   |
   v
PostgreSQL
```

### Project Structure

```text
habot-booking-backend/
│
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── extensions.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── booking.py
│   │   ├── lsa.py
│   │   ├── parent.py
│   │   ├── payment.py
│   │   └── user.py
│   │
│   ├── routes/
│   │   ├── auth.py
│   │   ├── bookings.py
│   │   ├── lsas.py
│   │   └── payments.py
│   │
│   └── services/
│       ├── __init__.py
│       └── booking_service.py
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_bookings.py
│   ├── test_errors.py
│   ├── test_lsas.py
│   └── test_payments.py
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run.py
```

# Database Design

The core booking domain contains Parent, LSA, Booking, and Payment entities.

Authentication is handled through the User entity.

```text
User
 |
 | 1 : 1
 |
Parent
 |
 | 1 : N
 |
BookingRequest
 |
 | N : 1
 |
LSAProfile

BookingRequest
 |
 | 1 : N
 |
PaymentEvent
```

## User

Stores authentication and authorization information.

Important fields:

- `id`
- `email`
- `password_hash`
- `role`
- `is_active`
- `created_at`

Passwords are stored as password hashes rather than plaintext values.

## Parent

Represents a parent using the booking platform.

Important fields:

- `id`
- `name`
- `email`
- `user_id`
- `created_at`

The `user_id` creates a one-to-one relationship between the authenticated User and Parent.

## LSAProfile

Represents a Learning Support Assistant.

Important fields include:

- `id`
- `name`
- `email`
- `skills`
- `is_active`

The skills field allows LSAs to be searched by required skills.

## BookingRequest

Represents a booking between a Parent and an LSA.

Important fields include:

- `id`
- `parent_id`
- `lsa_id`
- `start_time`
- `end_time`
- `status`

Booking statuses include pending and confirmed states, with payment processing capable of transitioning the booking state.

## PaymentEvent

Stores payment-related events associated with bookings.

Payment events are designed to support idempotent webhook processing.

---

# API Endpoints

## Authentication

Authentication endpoints provide user registration/login and JWT-based authentication.

Protected endpoints require:

```text
Authorization: Bearer <JWT>
```

JWT claims contain the user's role.

---

# Create Booking

```http
POST /api/v1/bookings/
```

Creates a new booking request.

### Request

```json
{
  "parent_id": 1,
  "lsa_id": 1,
  "start_time": "2026-08-15T10:00:00+00:00",
  "end_time": "2026-08-15T11:00:00+00:00"
}
```

### Successful Response

```http
201 Created
```

```json
{
  "id": 1,
  "parent_id": 1,
  "lsa_id": 1,
  "start_time": "2026-08-15T10:00:00+00:00",
  "end_time": "2026-08-15T11:00:00+00:00",
  "status": "pending"
}
```

### Validation

The endpoint validates:

- Request body presence
- Required fields
- Parent ID type
- LSA ID type
- Positive IDs
- Parent existence
- Parent ownership
- LSA existence
- LSA active status
- Datetime format
- Timezone information
- End time after start time
- Overlapping bookings

Only the authenticated parent associated with the requested Parent record can create bookings for that parent.

---

# Get Booking

```http
GET /api/v1/bookings/<booking_id>
```

Returns a booking belonging to the authenticated parent.

Access to another parent's booking is rejected.

---

# Search Available LSAs

```http
GET /api/v1/lsas/search/
```

Searches active LSAs based on skill and optional availability.

### Example

```http
GET /api/v1/lsas/search/?skill=ADHD
```

### Availability Search

```http
GET /api/v1/lsas/search/?skill=ADHD&start_time=2026-08-15T10:30:00Z&end_time=2026-08-15T11:30:00Z
```

The endpoint:

1. Filters inactive LSAs.
2. Optionally filters by skill.
3. Checks existing pending/confirmed bookings.
4. Excludes LSAs whose bookings overlap the requested time range.

The availability filtering is performed through database queries rather than loading bookings individually for every LSA, avoiding an N+1-style query pattern.

---

# Payment Webhook

```http
POST /api/v1/payments/webhook/
```

Receives payment events and updates booking state.

Payment success and failure events transition the associated booking appropriately.

Payment event handling is designed to be idempotent so that processing the same event more than once does not incorrectly apply the state transition multiple times.

---

# Preventing Double Bookings

Double-booking prevention is enforced at two levels.

## Application-Level Validation

Before creating a booking, the service checks for overlapping active bookings.

The overlap condition is:

```text
existing.start_time < requested.end_time
AND
existing.end_time > requested.start_time
```

This allows back-to-back bookings:

```text
10:00 ───── 11:00
              11:00 ───── 12:00
```

while rejecting overlapping bookings:

```text
10:00 ───── 11:00
       10:30 ───── 11:30
```

## Database-Level Protection

PostgreSQL provides the final integrity guarantee.

The database uses:

- `btree_gist`
- GiST indexing
- `tstzrange`
- an exclusion constraint for active bookings

This means the database itself prevents conflicting booking ranges even if two requests reach the database concurrently.

This is an important Poka-Yoke design decision because data integrity does not depend solely on application code.

---

# Authentication & Authorization

The API uses JWT authentication.

Protected endpoints use:

```python
@jwt_required()
```

Role-based authorization is implemented using:

```python
@role_required("parent")
```

The authorization layer distinguishes between:

- Authentication: Is the user logged in?
- Role authorization: Is the user a parent/LSA?
- Ownership authorization: Does the resource belong to the authenticated user?

For example, a parent can only create a booking for their own Parent record and cannot access another parent's booking.

---

# Error Handling

The API provides consistent JSON responses for application and HTTP errors.

Example:

```json
{
  "error": "Not Found",
  "message": "The requested URL was not found on the server."
}
```

JWT errors are also standardized.

### Missing token

```json
{
  "error": "Unauthorized",
  "message": "Authentication token is required"
}
```

### Invalid token

```json
{
  "error": "Unauthorized",
  "message": "Invalid authentication token"
}
```

### Expired token

```json
{
  "error": "Unauthorized",
  "message": "Authentication token has expired"
}
```

Unexpected internal exceptions are logged by the application while returning a safe generic response to the client.

---

# Database Migrations

Database schema changes are managed using Flask-Migrate/Alembic.

Example:

```bash
flask db migrate -m "migration message"
flask db upgrade
```

The repository contains migration scripts under:

```text
migrations/versions/
```

---

# Running with Docker

## Prerequisites

- Docker
- Docker Compose

## Start the application

```bash
docker compose up --build
```

The application runs inside the API container and PostgreSQL runs as a separate service.

## Stop the application

```bash
docker compose down
```

## Run migrations

```bash
docker compose exec api flask db upgrade
```

## Run tests

Tests can be executed in the configured Python environment with:

```bash
pytest
```

---

# Environment Variables

Create a `.env` file based on `.env.example`.

Example:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=habot_booking

JWT_SECRET_KEY=change-this-secret-key
```

Do not commit production secrets or the real `.env` file to version control.

---

# Testing

The project uses Pytest for automated testing.

The test suite covers:

- Authentication
- JWT validation
- Role authorization
- Ownership authorization
- Booking creation
- Booking validation
- Invalid datetime handling
- Missing timezone handling
- Parent/LSA validation
- Inactive LSAs
- Overlapping bookings
- Back-to-back bookings
- Database-level overlap protection
- LSA availability search
- Payment success
- Payment failure
- Payment idempotency
- Error handling
- HTTP error responses
- JWT error responses

Current test status:

```text
58 passed
0 warnings
```

Run the complete suite:

```bash
pytest
```

---

# Continuous Integration

GitHub Actions runs the automated test suite.

Workflow:

```text
Git Push
   |
   v
GitHub Actions
   |
   v
Install dependencies
   |
   v
Run Pytest
   |
   v
Pass / Fail
```

The workflow is located at:

```text
.github/workflows/tests.yml
```

---

# API Documentation

Swagger UI is available through:

```text
/docs
```

The API specification is stored under the application's static resources.

---

# Design Decisions

## Why Flask?

Flask was selected because the project requires a lightweight RESTful backend and the hiring brief explicitly allows Flask/Django-based implementations.

Flask provides:

- Lightweight routing
- Simple application structure
- Easy integration with SQLAlchemy
- Straightforward testing
- Flexible project organization

## MVC-style Architecture

The project uses a Flask MVC-style separation:

```text
Routes
  ↓
Services
  ↓
Models
  ↓
Database
```

Routes handle HTTP concerns while business logic is separated into services where appropriate.

## Why PostgreSQL?

PostgreSQL provides the relational integrity and advanced range/indexing capabilities required for reliable booking conflict prevention.

In particular, PostgreSQL's GiST/range functionality allows booking overlap constraints to be enforced at the database level.

## Why Database-Level Conflict Prevention?

Application checks alone can suffer from race conditions when multiple requests arrive simultaneously.

The database constraint provides a final integrity boundary.

This follows the Poka-Yoke principle described in the project requirements: the system should prevent mistakes through design rather than relying on human memory.

---

# Future Improvements

Potential production enhancements include:

- Refresh token rotation
- Rate limiting
- Structured logging
- API versioning strategy
- More granular permissions
- Production WSGI deployment
- Observability and metrics
- Background processing for external payment events
- Expanded API schema validation

These are intentionally outside the core prototype scope.

---

# Project Status

The backend prototype currently includes:

- Relational PostgreSQL schema
- SQLAlchemy models
- REST APIs
- JWT authentication
- Role-based authorization
- Ownership checks
- Booking validation
- Database-level double-booking prevention
- LSA availability search
- Payment webhook processing
- Automated tests
- Docker support
- Database migrations
- GitHub Actions CI
- Swagger UI

Test status:

```text
58 passed
0 warnings
```

---

# Author

**Anuranjan SB**

Python Backend Developer Candidate
