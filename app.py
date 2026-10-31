import csv
import hmac
import io
import json
import os
import secrets
import threading
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit, join_room

from analytics import compute_dashboard_payload
from database import (
    OPTIONS,
    SURVEY_META,
    clear_all_responses,
    clear_demo_responses,
    delete_response_by_id,
    fetch_all_responses,
    init_db,
    insert_response,
    seed_demo_data,
)

BASE_DIR = Path(__file__).resolve().parent


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env_file()
init_db()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "observatum-fallback-secret-key")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-this-password")

socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins="*",
    ping_interval=60,
    ping_timeout=30,
)

_listeners_lock = threading.Lock()
_active_admin_sids: set[str] = set()


def get_active_listener_count() -> int:
    with _listeners_lock:
        return len(_active_admin_sids)


def build_state_with_meta() -> dict:
    payload = compute_dashboard_payload()
    payload["active_listeners"] = get_active_listener_count()
    return payload


def broadcast_if_admins_listening() -> None:
    if get_active_listener_count() == 0:
        return
    payload = build_state_with_meta()
    socketio.emit("survey_update", payload, to="admins")


def is_admin_authenticated() -> bool:
    return bool(session.get("admin_authenticated") is True)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin_authenticated():
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Unauthorized"}), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)

    return wrapper


@app.route("/", methods=["GET"])
def survey_page():
    return render_template("survey.html", meta=SURVEY_META, options=OPTIONS)


@app.route("/api/submit", methods=["POST"])
def submit_survey():
    data = request.get_json(silent=True) or {}

    q1_id = str(data.get("q1_participant_id", "")).strip().upper()
    if not q1_id or len(q1_id) < 2 or len(q1_id) > 64:
        return jsonify({"ok": False, "error": "Question 1: Valid Identification Number is required."}), 400

    q2 = "N/A"
    single_fields = [
        ("q3_occupation", "Question 3 (Occupation)"),
        ("q4_area", "Question 4 (Area in KL)"),
        ("q5_mobile_provider", "Question 5 (Mobile Provider)"),
        ("q6_broadband_provider", "Question 6 (Fixed Broadband Provider)"),
        ("q7_disconnect_freq", "Question 7 (Disconnection Frequency)"),
        ("q8_phantom_signal", "Question 8 (Full Signal, No Internet)"),
        ("q13_support_satisfaction", "Question 13 (Customer Support Satisfaction)"),
        ("q14_price_value_match", "Question 14 (Price vs Stability Match)"),
        ("q15_auto_backup_support", "Question 15 (Emergency Backup/Rebate Support)"),
    ]

    cleaned = {
        "q1_participant_id": q1_id,
        "q2_dgcc_enrolled": q2,
    }

    for key, label in single_fields:
        val = str(data.get(key, "")).strip()
        if val not in OPTIONS[key]:
            return jsonify({"ok": False, "error": f"{label}: Please select a valid option."}), 400
        cleaned[key] = val

    try:
        q10 = int(data.get("q10_frustration_scale", 0))
    except (ValueError, TypeError):
        q10 = 0
    if q10 < 1 or q10 > 5:
        return jsonify({"ok": False, "error": "Question 10: Please select a frustration rating between 1 and 5."}), 400
    cleaned["q10_frustration_scale"] = q10

    multi_fields = [
        ("q9_worst_conditions", "Question 9", 1, 5),
        ("q11_impacted_activities", "Question 11", 1, 6),
        ("q12_coping_mechanisms", "Question 12", 1, 5),
        ("q16_top_improvements", "Question 16 (Select top 2)", 1, 2),
    ]

    for key, label, min_c, max_c in multi_fields:
        raw_list = data.get(key, [])
        if not isinstance(raw_list, list):
            return jsonify({"ok": False, "error": f"{label}: Invalid selection format."}), 400
        valid_items = [x for x in raw_list if x in OPTIONS[key]]
        if len(valid_items) < min_c:
            return jsonify({"ok": False, "error": f"{label}: Please select at least {min_c} option(s)."}), 400
        if len(valid_items) > max_c:
            return jsonify({"ok": False, "error": f"{label}: Please select at most {max_c} option(s)."}), 400
        cleaned[key] = valid_items

    q17 = str(data.get("q17_memorable_moment", "")).strip()[:1500]
    cleaned["q17_memorable_moment"] = q17
    cleaned["receipt_code"] = f"SDG9-KL-{secrets.token_hex(3).upper()}"

    saved = insert_response(cleaned, is_demo=False)
    broadcast_if_admins_listening()

    return jsonify({
        "ok": True,
        "receipt_code": saved["receipt_code"],
        "created_at": saved["created_at"],
    })


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if is_admin_authenticated():
        return redirect(url_for("admin_dashboard"))
    error = ""
    if request.method == "POST":
        pwd = str(request.form.get("password", ""))
        if hmac.compare_digest(pwd, ADMIN_PASSWORD):
            session["admin_authenticated"] = True
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        error = "ACCESS DENIED // INVALID CREDENTIALS"
    return render_template("login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard():
    initial_payload = build_state_with_meta()
    return render_template("admin.html", initial_payload=initial_payload, meta=SURVEY_META)


@app.route("/api/admin/state", methods=["GET"])
@admin_required
def api_admin_state():
    return jsonify({"ok": True, "payload": build_state_with_meta()})


@app.route("/api/admin/seed", methods=["POST"])
@admin_required
def api_admin_seed():
    body = request.get_json(silent=True) or {}
    count = max(1, min(100, int(body.get("count", 25))))
    inserted = seed_demo_data(count=count)
    payload = build_state_with_meta()
    broadcast_if_admins_listening()
    return jsonify({"ok": True, "inserted": inserted, "payload": payload})


@app.route("/api/admin/clear-demo", methods=["POST"])
@admin_required
def api_admin_clear_demo():
    removed = clear_demo_responses()
    payload = build_state_with_meta()
    broadcast_if_admins_listening()
    return jsonify({"ok": True, "removed": removed, "payload": payload})


@app.route("/api/admin/delete/<int:row_id>", methods=["POST"])
@admin_required
def api_admin_delete_row(row_id: int):
    deleted = delete_response_by_id(row_id)
    payload = build_state_with_meta()
    broadcast_if_admins_listening()
    return jsonify({"ok": deleted, "payload": payload})


@app.route("/api/admin/reset-all", methods=["POST"])
@admin_required
def api_admin_reset_all():
    removed = clear_all_responses()
    payload = build_state_with_meta()
    broadcast_if_admins_listening()
    return jsonify({"ok": True, "removed": removed, "payload": payload})


@app.route("/admin/export.csv", methods=["GET"])
@admin_required
def admin_export_csv():
    rows = fetch_all_responses()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id",
        "receipt_code",
        "created_at",
        "is_demo",
        "q1_participant_id",
                "q3_occupation",
        "q4_area",
        "q5_mobile_provider",
        "q6_broadband_provider",
        "q7_disconnect_freq",
        "q8_phantom_signal",
        "q9_worst_conditions",
        "q10_frustration_scale",
        "q11_impacted_activities",
        "q12_coping_mechanisms",
        "q13_support_satisfaction",
        "q14_price_value_match",
        "q15_auto_backup_support",
        "q16_top_improvements",
        "q17_memorable_moment",
    ])
    for r in rows:
        writer.writerow([
            r["id"],
            r["receipt_code"],
            r["created_at"],
            r["is_demo"],
            r["q1_participant_id"],
                        r["q3_occupation"],
            r["q4_area"],
            r["q5_mobile_provider"],
            r["q6_broadband_provider"],
            r["q7_disconnect_freq"],
            r["q8_phantom_signal"],
            " | ".join(r["q9_worst_conditions"]),
            r["q10_frustration_scale"],
            " | ".join(r["q11_impacted_activities"]),
            " | ".join(r["q12_coping_mechanisms"]),
            r["q13_support_satisfaction"],
            r["q14_price_value_match"],
            r["q15_auto_backup_support"],
            " | ".join(r["q16_top_improvements"]),
            r["q17_memorable_moment"],
        ])
    csv_bytes = buf.getvalue().encode("utf-8-sig")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=observatum_sdg9_kl_survey.csv"},
    )


@app.route("/admin/export.json", methods=["GET"])
@admin_required
def admin_export_json():
    export_obj = {
        "meta": SURVEY_META,
        "analytics": build_state_with_meta(),
        "raw_responses": fetch_all_responses(),
    }
    return Response(
        json.dumps(export_obj, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=observatum_sdg9_kl_survey.json"},
    )


@socketio.on("connect")
def handle_ws_connect():
    if not is_admin_authenticated():
        return False
    with _listeners_lock:
        _active_admin_sids.add(request.sid)
    join_room("admins")
    emit("survey_update", build_state_with_meta())


@socketio.on("disconnect")
def handle_ws_disconnect():
    with _listeners_lock:
        _active_admin_sids.discard(request.sid)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5005"))
    socketio.run(app, host="127.0.0.1", port=port, debug=False)
