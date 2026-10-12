from typing import Optional

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
)

from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ------------------------------------------------------------------
# POST /auth/register
# ------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "attendee").strip().lower()

    # --- validation ---
    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400

    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email address"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if role not in ("attendee", "organizer"):
        return jsonify({"error": "role must be 'attendee' or 'organizer'"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # --- create user ---
    user = User(name=name, email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "User registered successfully",
        "user": user.to_dict(),
        "access_token": token,
    }), 201


# ------------------------------------------------------------------
# POST /auth/login
# ------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": token,
    }), 200


# ------------------------------------------------------------------
# GET /auth/me — return current user
# ------------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200


# ------------------------------------------------------------------
# Helpers (used by app.py)
# ------------------------------------------------------------------
def current_user():
    # type: () -> Optional[User]
    """Return the User object from the JWT, or None."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(int(user_id)) if user_id else None
    except Exception:
        return None