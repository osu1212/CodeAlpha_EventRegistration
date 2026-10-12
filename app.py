import os
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

from models import db, User, Event, Registration
from auth import auth_bp

# ------------------------------------------------------------------
# App config
# ------------------------------------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///events.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # no expiry for demo simplicity

db.init_app(app)
jwt = JWTManager(app)

# Register auth blueprint (routes under /auth/*)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def current_user():
    """Return the User object from the JWT, or None."""
    try:
        user_id = get_jwt_identity()
        return User.query.get(int(user_id)) if user_id else None
    except Exception:
        return None


def parse_date(value):
    """Accept ISO format (2025-12-31T18:00) or date-only (2025-12-31)."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ------------------------------------------------------------------
# Frontend
# ------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ==================================================================
# EVENT ROUTES
# ==================================================================

# GET /events — list all events (public)
@app.route("/events", methods=["GET"])
def list_events():
    query = Event.query

    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))

    location = request.args.get("location", "").strip()
    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))

    events = query.order_by(Event.date.asc()).all()
    return jsonify([e.to_dict() for e in events]), 200


# GET /events/<id> — single event details (public)
@app.route("/events/<int:event_id>", methods=["GET"])
def event_detail(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event.to_dict(include_organizer=True)), 200


# POST /events — create event (organizer only)
@app.route("/events", methods=["POST"])
@jwt_required()
def create_event():
    user = current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role != "organizer":
        return jsonify({"error": "Only organizers can create events"}), 403

    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    date_raw = (data.get("date") or "").strip()
    location = (data.get("location") or "").strip()
    capacity = data.get("capacity", 100)

    if not title or not date_raw:
        return jsonify({"error": "title and date are required"}), 400

    event_date = parse_date(date_raw)
    if not event_date:
        return jsonify({"error": "Invalid date. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM"}), 400

    try:
        capacity = int(capacity)
        if capacity <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "capacity must be a positive integer"}), 400

    event = Event(
        title=title,
        description=description,
        date=event_date,
        location=location,
        capacity=capacity,
        organizer_id=user.id,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({
        "message": "Event created",
        "event": event.to_dict(),
    }), 201


# DELETE /events/<id> — delete own event (organizer only)
@app.route("/events/<int:event_id>", methods=["DELETE"])
@jwt_required()
def delete_event(event_id):
    user = current_user()
    if not user or user.role != "organizer":
        return jsonify({"error": "Organizer role required"}), 403

    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    if event.organizer_id != user.id:
        return jsonify({"error": "You can only delete your own events"}), 403

    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Event deleted"}), 200


# GET /events/<id>/registrations — view who registered (organizer only)
@app.route("/events/<int:event_id>/registrations", methods=["GET"])
@jwt_required()
def event_registrations(event_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event.organizer_id != user.id:
        return jsonify({"error": "Only the organizer can view registrations"}), 403

    return jsonify({
        "event": event.to_dict(),
        "registrations": [
            {
                "registration_id": r.id,
                "user": r.user.to_dict(),
                "registered_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in event.registrations
        ],
        "total": len(event.registrations),
        "spots_left": event.spots_left,
    }), 200


# ==================================================================
# REGISTRATION ROUTES
# ==================================================================

# POST /events/<id>/register — sign up for an event
@app.route("/events/<int:event_id>/register", methods=["POST"])
@jwt_required()
def register_for_event(event_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event.organizer_id == user.id:
        return jsonify({"error": "Organizers cannot register for their own event"}), 400

    existing = Registration.query.filter_by(user_id=user.id, event_id=event.id).first()
    if existing:
        return jsonify({"error": "You are already registered for this event"}), 409

    if event.spots_left <= 0:
        return jsonify({"error": "Event is full"}), 409

    reg = Registration(user_id=user.id, event_id=event.id)
    db.session.add(reg)
    db.session.commit()

    return jsonify({
        "message": "Registered successfully",
        "registration": reg.to_dict(include_event=True),
    }), 201


# GET /registrations/me — my registrations
@app.route("/registrations/me", methods=["GET"])
@jwt_required()
def my_registrations():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    regs = (
        Registration.query
        .filter_by(user_id=user.id)
        .order_by(Registration.created_at.desc())
        .all()
    )
    return jsonify([r.to_dict(include_event=True) for r in regs]), 200


# DELETE /registrations/<id> — cancel my registration
@app.route("/registrations/<int:reg_id>", methods=["DELETE"])
@jwt_required()
def cancel_registration(reg_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    reg = Registration.query.get(reg_id)
    if not reg:
        return jsonify({"error": "Registration not found"}), 404

    if reg.user_id != user.id:
        return jsonify({"error": "You can only cancel your own registrations"}), 403

    db.session.delete(reg)
    db.session.commit()
    return jsonify({"message": "Registration cancelled"}), 200


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)