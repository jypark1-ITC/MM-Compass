"""MM-Compass 실행 파일

  py app.py            → 이 PC에서만 접속 (http://127.0.0.1:8800)
  py app.py --lan      → 같은 사내망의 다른 PC도 접속 (http://<이 PC IP>:8800)
"""
import sys
from gadong import create_app

app = create_app()
if __name__ == "__main__":
    host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
    from werkzeug.serving import run_simple
    print(f"MM-Compass 실행 중 → http://{'<이 PC IP>' if host == '0.0.0.0' else '127.0.0.1'}:8800  (끄려면 Ctrl+C)")
    run_simple(host, 8800, app, threaded=True)
