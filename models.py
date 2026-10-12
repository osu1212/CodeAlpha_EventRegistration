from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Python 3.9 note: use pbkdf2 instead of scrypt (scrypt unavailable on some system Pythons)
PASSWORD_METHOD = "pbkdf2:sha256"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="attendee")  # "attendee" | "organizer"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship("Event", backref="organizer", lazy=True)
    registrations = db.relationship(
        "Registration",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method=PASSWORD_METHOD)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), default="")
    capacity = db.Column(db.Integer, default=100)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registrations = db.relationship(
        "Registration",
        backref="event",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def spots_taken(self):
        return len(self.registrations)

    @property
    def spots_left(self):
        return max(self.capacity - self.spots_taken, 0)

    def to_dict(self, include_organizer=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat() if self.date else None,
            "location": self.location,
            "capacity": self.capacity,
            "spots_taken": self.spots_taken,
            "spots_left": self.spots_left,
            "organizer_id": self.organizer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_organizer and self.organizer:
            data["organizer"] = {
                "id": self.organizer.id,
                "name": self.organizer.name,
                "email": self.organizer.email,
            }
        return data


class Registration(db.Model):
    __tablename__ = "registrations"
    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_event=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_event and self.event:
            data["event"] = self.event.to_dict()
        return data