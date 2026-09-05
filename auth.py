"""
KAPA Bank Authentication & Security Module
Handles session management, RBAC decorators, CSRF validation, and audit logging.
"""
import os
import secrets
import logging
from functools import wraps
from flask import session, redirect, url_for, request, abort, render_template
from database import get_connection, dictfetchone

logger = logging.getLogger(__name__)

def generate_csrf_token():
    """Generates or retrieves the CSRF token for the active session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def validate_csrf():
    """Validates the CSRF token submitted with POST/PUT/DELETE requests."""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    expected = session.get("csrf_token")
    if not expected or not token or not secrets.compare_digest(token, expected):
        logger.warning("CSRF validation failed for IP %s on route %s", request.remote_addr, request.path)
        return False
    return True

def get_current_user():
    """Retrieves authenticated user summary from the session."""
    if "user_id" not in session:
        return None
    cid = session.get("customer_id")
    is_demo = (cid == 21) or (str(session.get("email", "")).lower() == "demo@kapabank.com")
    return {
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "role": session.get("role"),
        "customer_id": cid,
        "name": session.get("user_name", "User"),
        "is_demo": is_demo
    }

def login_required(f):
    """Ensures a user is authenticated before allowing route access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Restricts route access exclusively to users with the ADMIN role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "ADMIN":
            logger.warning("Unauthorized admin access attempt by user_id %s on %s", session.get("user_id"), request.path)
            return render_template("error.html", 
                                   title="Access Forbidden (403)", 
                                   message="You do not possess administrative privileges to access this area.",
                                   back_url="/",
                                   back_label="Return to Portal"), 403
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    """Restricts route access to users with CUSTOMER role; redirects ADMIN to /admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        if session.get("role") == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        if not session.get("customer_id"):
            return render_template("error.html", 
                                   title="Customer Account Missing", 
                                   message="Your user login is not linked to an active customer profile.",
                                   back_url="/logout",
                                   back_label="Log Out"), 403
        return f(*args, **kwargs)
    return decorated_function

def log_audit(action, entity_type=None, entity_id=None, details=None, user_id=None):
    """Records an entry in the AUDIT_LOG table."""
    uid = user_id or session.get("user_id")
    ip_addr = request.remote_addr or "127.0.0.1"
    
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (:1, :2, :3, :4, :5, :6)
        """, (uid, action, entity_type, entity_id, details, ip_addr))
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        logger.error("Failed to write audit log (%s): %s", action, str(e))
