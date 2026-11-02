import sqlite3, datetime as dt
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, display TEXT NOT NULL,
  pw_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','uploader','viewer')),
  dept TEXT DEFAULT '', active INTEGER DEFAULT 1,
  fail_count INTEGER DEFAULT 0, locked_until TEXT DEFAULT '', created_at TEXT);
CREATE TABLE IF NOT EXISTS uploads(
  id INTEGER PRIMARY KEY, user_id INTEGER, dept TEXT, kind TEXT, week TEXT,
  orig_name TEXT, stored_name TEXT, size INTEGER, status TEXT, note TEXT, uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS weeks(
  label TEXT PRIMARY KEY, title TEXT, published INTEGER DEFAULT 0, published_at TEXT, comment TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, at TEXT, user TEXT, action TEXT, detail TEXT);
"""

def now(): return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close(_e=None):
    d = g.pop("db", None)
    if d is not None: d.close()

def init_app(app):
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        c.executescript(SCHEMA)
    app.teardown_appcontext(close)

def audit(user, action, detail=""):
    d = get(); d.execute("INSERT INTO audit(at,user,action,detail) VALUES(?,?,?,?)", (now(), user, action, detail)); d.commit()

def migrate(app):
    """업로드 상태 체계 변경: 접수 → 제출 (관리자 반영 확정 전까지 계산에서 제외)"""
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        c.execute("UPDATE uploads SET status='제출' WHERE status='접수'")
        # 회원가입 신청: users.active = -1 (승인 대기) · 신청 내용은 req_note
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        if "req_note" not in cols: c.execute("ALTER TABLE users ADD COLUMN req_note TEXT DEFAULT ''")
        if "depts" not in cols: c.execute("ALTER TABLE users ADD COLUMN depts TEXT DEFAULT ''")   # 담당 부서 여러 개 (JSON)

def sync_published(app):
    """published 폴더와 주차 목록 맞추기 (켤 때마다)
    - 새로 들어온 주차 폴더(Claude가 만들어 넣은 것 등)는 자동 등록·게시
    - 폴더 안에 RETIRED.txt 가 있으면 목록에서 뺌 (잘못 붙은 주차 정리용)"""
    import os, re
    pub = os.path.join(app.config["STORAGE"], "published")
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        for label in sorted(os.listdir(pub)):
            d = os.path.join(pub, label)
            if not os.path.isdir(d) or not re.fullmatch(r"\d{4}-\d{2}-W\d", label): continue
            if os.path.exists(os.path.join(d, "RETIRED.txt")):
                c.execute("DELETE FROM weeks WHERE label=?", (label,)); continue
            if os.path.exists(os.path.join(d, "meeting.html")):
                y, m, w = label[:4], int(label[5:7]), label.split("W")[-1]
                c.execute("INSERT OR IGNORE INTO weeks(label,title,published,published_at) VALUES(?,?,1,?)", (label, f"{y}년 {m}월 {w}주차", now()))
