# CodeAlpha_EventRegistration

This project is an Event Registration System API built with **Flask** + **SQLite** + **JWT** for the CodeAlpha Backend Development Internship (Task 2).

Organizers can create events, attendees can register, and everyone can manage their own registrations — all behind secure JWT authentication.

## Features
- User registration & login with JWT authentication
- Two roles: **organizer** and **attendee**
- Organizers create, view, and delete their own events
- Attendees browse events, register, and cancel registrations
- Capacity enforcement (event cannot overfill)
- Duplicate registration prevention
- Event search by title and location
- Organizers can view the full attendee list per event
- Session persistence on the frontend via localStorage

## Tech Stack
- Python 3.9+
- Flask
- Flask-SQLAlchemy
- Flask-JWT-Extended
- SQLite
- Werkzeug (password hashing, pbkdf2:sha256)

## Setup

```bash
git clone https://github.com/osu1212/CodeAlpha_EventRegistration.git
cd CodeAlpha_EventRegistration
python3 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Then open http://localhost:5000

## API Endpoints

### Auth
| Method | Route | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a new user (attendee or organizer) |
| POST | `/auth/login` | Public | Login and receive a JWT |
| GET | `/auth/me` | JWT | Get the currently logged-in user |

### Events
| Method | Route | Auth | Description |
|---|---|---|---|
| GET | `/events` | Public | List all events (`?search=` and `?location=` supported) |
| GET | `/events/<id>` | Public | View a single event with organizer info |
| POST | `/events` | Organizer JWT | Create a new event |
| DELETE | `/events/<id>` | Organizer JWT | Delete your own event |
| GET | `/events/<id>/registrations` | Organizer JWT | View all registrations for your event |

### Registrations
| Method | Route | Auth | Description |
|---|---|---|---|
| POST | `/events/<id>/register` | JWT | Register for an event |
| GET | `/registrations/me` | JWT | List my registrations |
| DELETE | `/registrations/<id>` | JWT | Cancel my own registration |

## Example — Register + create an event

```bash
# 1. Register an organizer
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","password":"password123","role":"organizer"}'

# Response contains: { "access_token": "..." }

# 2. Create an event (paste the token)
curl -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer PASTE_TOKEN_HERE" \
  -d '{"title":"Python Workshop","date":"2025-12-31T18:00","location":"Lagos","capacity":50}'

# 3. Anyone can list events (no auth needed)
curl http://localhost:5000/events
```

## Project Structure

```
CodeAlpha_EventRegistration/
├── app.py               # Flask app + event & registration routes
├── models.py            # User, Event, Registration models
├── auth.py              # /auth routes + JWT helpers
├── requirements.txt
├── templates/
│   └── index.html       # Demo frontend
├── static/
│   └── style.css
└── README.md
```

## Author
**Osutuk Ndifreke** — CodeAlpha Backend Development Intern

## License
MIT