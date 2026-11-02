import secrets, datetime as dt, functools
from flask import session, request, redirect, url_for, abort, g, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

MAX_FAIL, LOCK_MIN = 5, 10

def hash_pw(pw): return generate_password_hash(pw)

def current_user():
    uid = session.get("uid")
    if not uid: return None
    u = db.get().execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
    return u

def login_required(*roles):
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **k):
            u = current_user()
            if not u: return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles: abort(403)
            g.user = u
            return fn(*a, **k)
        return wrap
    return deco

def csrf_token():
    if "csrf" not in session: session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]

def check_csrf():
    t = request.form.get("csrf", "")
    if not t or not secrets.compare_digest(t, session.get("csrf", "")): abort(400, "잘못된 요청입니다 (CSRF)")

def init_app(app):
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["me"] = current_user

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            check_csrf()
            name = request.form.get("username", "").strip(); pw = request.form.get("password", "")
            d = db.get(); u = d.execute("SELECT * FROM users WHERE username=?", (name,)).fetchone()
            nowt = dt.datetime.now()
            if u and u["locked_until"] and nowt < dt.datetime.fromisoformat(u["locked_until"]):
                flash(f"로그인 시도가 많아 잠시 잠겼습니다. {LOCK_MIN}분 후 다시 시도하세요."); return render_template("login.html"), 429
            if u and u["active"] == -1 and check_password_hash(u["pw_hash"], pw):
                flash("가입 신청이 아직 승인되지 않았습니다. 관리자 승인 후 로그인할 수 있습니다."); return render_template("login.html")
            if u and u["active"] == 1 and check_password_hash(u["pw_hash"], pw):
                d.execute("UPDATE users SET fail_count=0, locked_until='' WHERE id=?", (u["id"],)); d.commit()
                session.clear(); session.permanent = True; session["uid"] = u["id"]
                db.audit(name, "login")
                nxt = request.args.get("next", "")
                return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("home"))
            if u:
                fc = u["fail_count"] + 1
                lock = (nowt + dt.timedelta(minutes=LOCK_MIN)).isoformat() if fc >= MAX_FAIL else ""
                d.execute("UPDATE users SET fail_count=?, locked_until=? WHERE id=?", (0 if lock else fc, lock, u["id"])); d.commit()
            db.audit(name or "-", "login_fail")
            flash("아이디 또는 비밀번호가 맞지 않습니다.")
        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        """회원가입 신청 → 승인 대기(active=-1) · 관리자가 사용자 화면에서 승인"""
        import re, os, json
        from flask import current_app
        p = os.path.join(current_app.config["BASE_DIR"], "gadong", "depts.json")
        depts = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
        f = {k: request.form.get(k, "").strip() for k in ("username", "display", "email", "role", "dept", "note")} if request.method == "POST" else {"role": "uploader"}
        if request.method == "POST":
            check_csrf()
            pw, pw2 = request.form.get("password", ""), request.form.get("password2", "")
            d = db.get(); err = ""
            if not re.fullmatch(r"[A-Za-z0-9._\-]{4,30}", f["username"]): err = "아이디는 영문·숫자 4~30자로 입력해 주세요."
            elif not f["display"]: err = "이름을 입력해 주세요."
            elif not re.fullmatch(r"[A-Za-z0-9._%+\-]+@itcen\.com", f["email"], re.I): err = "회사 메일 주소(예: 아이디@itcen.com)를 입력해 주세요."
            elif f["role"] not in ("uploader", "viewer"): err = "사용 목적을 골라 주세요."
            elif f["role"] == "uploader" and f["dept"] not in depts: err = "투입계획을 올리려면 소속 부서를 골라 주세요."
            elif len(pw) < 8: err = "비밀번호는 8자 이상이어야 합니다."
            elif pw != pw2: err = "비밀번호 확인이 맞지 않습니다."
            elif d.execute("SELECT 1 FROM users WHERE username=?", (f["username"],)).fetchone(): err = "이미 있는 아이디입니다. 다른 아이디를 써 주세요."
            elif d.execute("SELECT 1 FROM users WHERE lower(email)=?", (f["email"].lower(),)).fetchone(): err = "이미 가입(신청)된 메일 주소입니다. 관리자에게 문의해 주세요."
            elif d.execute("SELECT COUNT(*) FROM users WHERE active=-1").fetchone()[0] >= 50: err = "가입 신청이 많이 밀려 있습니다. 관리자에게 직접 문의해 주세요."
            if err:
                flash(err); return render_template("signup.html", f=f, depts=depts)
            d.execute("INSERT INTO users(username,display,pw_hash,role,dept,active,created_at,req_note,email) VALUES(?,?,?,?,?,-1,?,?,?)",
                      (f["username"], f["display"][:20], hash_pw(pw), f["role"], f["dept"] if f["dept"] in depts else "", db.now(), f["note"][:200], f["email"].lower()))
            d.commit(); db.audit(f["username"], "signup_request", f"{f['display']} · {f['role']} · {f['dept']}")
            return render_template("signup.html", f=f, depts=depts, done=True)
        return render_template("signup.html", f=f, depts=depts)

    @app.route("/logout", methods=["POST"])
    def logout():
        check_csrf(); session.clear(); return redirect(url_for("login"))
