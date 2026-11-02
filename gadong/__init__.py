"""MM-Compass — 인력 가동 현황 사이트 (뼈대)

역할
  admin    : 관리자. 전체 대시보드, 업로드 현황, 사용자·주차 관리, 재계산
  uploader : 업로드 담당자. 담당 부서 투입계획 업로드, 본인 업로드 이력
  viewer   : 회의 참석자. 게시된 회의용 대시보드 보기
"""
import os, secrets
from flask import Flask, g
from . import db, auth, views

def create_app():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__)
    storage = os.path.join(base, "storage")
    os.makedirs(os.path.join(storage, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(storage, "published"), exist_ok=True)
    key_file = os.path.join(storage, "secret.key")
    if not os.path.exists(key_file):
        with open(key_file, "w") as f: f.write(secrets.token_hex(32))
    app.config.update(
        SECRET_KEY=open(key_file).read().strip(),
        BASE_DIR=base, STORAGE=storage,
        DB_PATH=os.path.join(storage, "gadong.db"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,          # 업로드 최대 20MB
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=8 * 3600,           # 8시간 후 다시 로그인
        TEMPLATES_AUTO_RELOAD=True,                    # 화면(html) 파일을 바꾸면 사이트를 다시 켜지 않아도 바로 반영
    )
    db.init_app(app)
    db.migrate(app)
    db.sync_published(app)
    # 계산 도중 사이트가 꺼졌거나 PC가 재시작됐다면 '계산 중'이 영원히 남아 재계산 버튼이 잠김 → 켤 때 '중단됨'으로 정리
    try:
        import datetime as _dt
        from engine import run as _er
        _wk = os.path.join(storage, "work")
        for _L in (os.listdir(_wk) if os.path.isdir(_wk) else []):
            _s = _er.read_status(storage, _L)
            if _s and _s.get("state") == "running":
                _er._set(storage, _L, state="error", finished=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         msg="계산 도중 사이트가 꺼지거나 다시 켜져서 중단되었습니다.", cause="계산 중단 (사이트 재시작)",
                         hint="'재계산'을 다시 눌러 주세요. 이전 계산본과 게시본은 그대로입니다.", files=[])
    except Exception:
        pass
    auth.init_app(app)
    views.init_app(app)
    from . import submit
    submit.init_app(app)
    from . import backup
    if not os.environ.get("GADONG_NO_BACKUP"): backup.start_scheduler(app)   # 하루 1번 자동 백업

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp
    return app
