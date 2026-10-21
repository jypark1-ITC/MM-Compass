"""관리 명령
  py manage.py init                 : 처음 한 번 — 관리자 계정 만들기 + 게시본 주차 등록
  py manage.py adduser 아이디 역할 [부서]  : 계정 추가 (역할: admin / uploader / viewer)
  py manage.py resetpw [아이디]      : 비밀번호 재설정 + 잠금 해제 (비밀번호재설정.bat)
"""
import sys, os, getpass, sqlite3
from gadong import create_app
from gadong.auth import hash_pw
from gadong import db

app = create_app()

def register_weeks(c):
    pub = os.path.join(app.config["STORAGE"], "published")
    for label in sorted(os.listdir(pub)):
        if not os.path.isdir(os.path.join(pub, label)): continue
        y, m, w = label[:4], int(label[5:7]), label.split("W")[-1]
        c.execute("INSERT OR IGNORE INTO weeks(label,title,published,published_at) VALUES(?,?,1,datetime('now','localtime'))", (label, f"{y}년 {m}월 {w}주차"))

def adduser(un, role, dept=""):
    pw = getpass.getpass(f"{un} 비밀번호 (8자 이상): ")
    if len(pw) < 8: sys.exit("8자 이상이어야 합니다.")
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        c.execute("INSERT INTO users(username,display,pw_hash,role,dept,created_at) VALUES(?,?,?,?,?,datetime('now','localtime'))", (un, un, hash_pw(pw), role, dept))
    print(f"{un} ({role}) 만들었습니다.")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        with sqlite3.connect(app.config["DB_PATH"]) as c: register_weeks(c)
        un = input("관리자 아이디: ").strip() or "admin"; adduser(un, "admin")
    elif cmd == "resetpw":
        with sqlite3.connect(app.config["DB_PATH"]) as c:
            rows = c.execute("SELECT username, role, active FROM users ORDER BY role, username").fetchall()
        if not rows:
            print("등록된 계정이 없습니다. 관리자 계정을 새로 만듭니다.")
            un = input("관리자 아이디: ").strip() or "admin"; adduser(un, "admin"); sys.exit()
        print("등록된 계정:")
        for r in rows: print(f"  - {r[0]}  ({r[1]}{'' if r[2] else ', 꺼짐'})")
        un = (sys.argv[2] if len(sys.argv) > 2 else input("비밀번호를 바꿀 아이디: ")).strip()
        if un not in [r[0] for r in rows]: sys.exit(f"'{un}' 계정이 없습니다.")
        pw = getpass.getpass("새 비밀번호 (8자 이상, 입력해도 화면에 안 보이는 게 정상): ")
        if len(pw) < 8: sys.exit("8자 이상이어야 합니다.")
        if getpass.getpass("한 번 더 입력: ") != pw: sys.exit("두 번 입력한 비밀번호가 다릅니다.")
        with sqlite3.connect(app.config["DB_PATH"]) as c:
            c.execute("UPDATE users SET pw_hash=?, fail_count=0, locked_until='', active=1 WHERE username=?", (hash_pw(pw), un))
            c.execute("INSERT INTO audit(at,user,action,detail) VALUES(datetime('now','localtime'),?,?,?)", ("(PC)", "pw_reset_cli", un))
        print(f"{un} 비밀번호를 바꾸고 잠금도 풀었습니다. 이제 로그인하세요.")
    elif cmd == "adduser" and len(sys.argv) >= 4:
        adduser(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    else:
        print(__doc__)
