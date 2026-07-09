import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import json
import ssl
import traceback
import os
import socket

# 全てのソケット通信にデフォルトの30秒タイムアウトを設定 (無応答ハングの完全回避)
socket.setdefaulttimeout(30)

PORT = int(os.environ.get("PORT", 10200))
ACCESS_KEY = "a9b2c8d4"

# SSL証明書検証をスキップするコンテキストを作成 (SSL検証エラー回避用)
ssl_context = ssl._create_unverified_context()

BASE_DIR = os.path.abspath("/opt/colab-gguf-chat" if os.path.exists("/opt/colab-gguf-chat") else ".")

def get_safe_path(relative_path):
    normalized_rel = os.path.normpath(relative_path.replace('\x00', ''))
    target_abs = os.path.abspath(os.path.join(BASE_DIR, normalized_rel))
    if not target_abs.startswith(BASE_DIR):
        raise PermissionError("Access denied: path is outside the workspace.")
    return target_abs

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def check_auth(self):
        # 1. URLパラメータのチェック
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        url_key = query_params.get('key', [''])[0]
        if url_key == ACCESS_KEY:
            return True

        # 2. Cookieのチェック
        cookie_header = self.headers.get('Cookie', '')
        if cookie_header:
            cookies = {}
            for cookie in cookie_header.split(';'):
                parts = cookie.strip().split('=', 1)
                if len(parts) == 2:
                    cookies[parts[0]] = parts[1]
            if cookies.get('access_key') == ACCESS_KEY:
                return True

        return False

    def send_login_html(self):
        login_html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ログイン - Colab Chat UI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0b0f19;
            --panel-bg: rgba(17, 24, 39, 0.7);
            --panel-border: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-color: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.15);
        }
        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        .login-card {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(16px);
            text-align: center;
            box-sizing: border-box;
        }
        h2 {
            margin-top: 0;
            font-size: 1.75rem;
            font-weight: 600;
            color: #a5b4fc;
        }
        p {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 24px;
        }
        input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            color: white;
            font-size: 1rem;
            margin-bottom: 16px;
            box-sizing: border-box;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 8px var(--accent-glow);
        }
        button {
            width: 100%;
            padding: 12px;
            background: var(--accent-color);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
        }
        button:hover {
            opacity: 0.9;
        }
        button:active {
            transform: scale(0.98);
        }
        .error-msg {
            color: #ef4444;
            font-size: 0.85rem;
            margin-top: 12px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Colab Chat UI</h2>
        <p>サーバーへのアクセスが保護されています。<br>アクセスキーを入力してください。</p>
        <input type="password" id="access-key-input" placeholder="アクセスキーを入力...">
        <button id="login-btn">認証する</button>
        <div class="error-msg" id="error-msg">アクセスキーが正しくありません。</div>
    </div>

    <script>
        // URLパラメータからの自動キー保存
        const urlParams = new URLSearchParams(window.location.search);
        const urlKey = urlParams.get('key');
        if (urlKey) {
            document.cookie = "access_key=" + urlKey + "; path=/; max-age=31536000; SameSite=Strict";
            window.location.href = window.location.pathname; // パラメータを消去してリダイレクト
        }

        const loginBtn = document.getElementById('login-btn');
        const keyInput = document.getElementById('access-key-input');
        const errorMsg = document.getElementById('error-msg');

        async function doLogin() {
            const key = keyInput.value.trim();
            if (!key) return;

            // クッキーにキーをセットしてリロードして検証させる
            document.cookie = "access_key=" + key + "; path=/; max-age=31536000; SameSite=Strict";
            
            // 検証のためにリロード
            window.location.reload();
        }

        loginBtn.addEventListener('click', doLogin);
        keyInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                doLogin();
            }
        });

        // リロード後にここに来た＝クッキーのキーが間違っていたということなのでエラー表示
        if (document.cookie && document.cookie.includes('access_key')) {
            errorMsg.style.display = 'block';
        }
    </script>
</body>
</html>
"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(login_html.encode('utf-8'))

    def do_GET(self):
        # 認証チェック
        if not self.check_auth():
            if self.path.startswith('/search') or self.path.startswith('/proxy'):
                self.send_response(401)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error": "Unauthorized"}')
            else:
                self.send_login_html()
            return

        # 静的ファイル配信 (MIMEブロック対策)
        if self.path in ('/', '/index.html'):
            try:
                html_path = "/opt/colab-gguf-chat/index.html" if os.path.exists("/opt/colab-gguf-chat") else "./index.html"
                with open(html_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(404)
                self.end_headers()
            return

        elif self.path == '/style.css':
            try:
                css_path = "/opt/colab-gguf-chat/style.css" if os.path.exists("/opt/colab-gguf-chat") else "./style.css"
                with open(css_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/css; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(404)
                self.end_headers()
            return

        elif self.path == '/app.js':
            try:
                js_path = "/opt/colab-gguf-chat/app.js" if os.path.exists("/opt/colab-gguf-chat") else "./app.js"
                with open(js_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/javascript; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(404)
                self.end_headers()
            return

        # 検索中継API
        elif self.path.startswith('/search?'):
            try:
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                query = query_params.get('q', [''])[0]
                
                if not query:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Query is empty"}')
                    return
                    
                print(f"[Python Server] Webを検索中: {query}", flush=True)
                results = self.search_searxng(query)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(results, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                err_msg = {"error": str(e)}
                self.wfile.write(json.dumps(err_msg).encode('utf-8'))
            return
            
        # 過去ログ検索API (過去ログRAG用)
        elif self.path.startswith('/search-history?'):
            try:
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                query = query_params.get('q', [''])[0]
                
                if not query:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'[]')
                    return
                
                print(f"[Python Server] 過去ログを検索中: {query}", flush=True)
                
                history_path = "/opt/colab-gguf-chat/chat_history.json" if os.path.exists("/opt/colab-gguf-chat") else "./chat_history.json"
                history_data = []
                if os.path.exists(history_path):
                    with open(history_path, "r", encoding="utf-8") as hf:
                        history_data = json.load(hf)
                
                # 簡易N-gram(Bigram)生成関数
                def get_bigrams(text):
                    clean_text = "".join(c.lower() for c in text if c.isalnum() and not c.isspace())
                    return {clean_text[i:i+2] for i in range(len(clean_text) - 1)}
                
                query_bigrams = get_bigrams(query)
                matched_threads = []
                
                if query_bigrams:
                    for thread in history_data:
                        thread_text = ""
                        for msg in thread.get("messages", []):
                            thread_text += " " + msg.get("content", "")
                        
                        thread_bigrams = get_bigrams(thread_text)
                        # 積集合(共通するBigram)の数をスコアとする
                        score = len(query_bigrams.intersection(thread_bigrams))
                        
                        if score > 0:
                            matched_threads.append((score, thread))
                
                # スコア順にソートし、上位2件を抽出
                matched_threads.sort(key=lambda x: x[0], reverse=True)
                results = [item[1] for item in matched_threads[:2]]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(results, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                err_msg = {"error": str(e)}
                self.wfile.write(json.dumps(err_msg).encode('utf-8'))
            return

        elif self.path == '/list-skills':
            try:
                skills_dir = "/opt/colab-gguf-chat/skills" if os.path.exists("/opt/colab-gguf-chat") else "./skills"
                os.makedirs(skills_dir, exist_ok=True)
                
                # スキルフォルダが空ならデフォルトスキルを生成
                if not os.listdir(skills_dir):
                    self.init_default_skills(skills_dir)
                
                skills_list = []
                import re
                for entry in os.scandir(skills_dir):
                    if entry.is_dir():
                        skill_md_path = os.path.join(entry.path, "SKILL.md")
                        if os.path.exists(skill_md_path):
                            with open(skill_md_path, "r", encoding="utf-8") as sf:
                                content = sf.read()
                            
                            # フロントマッターの簡易パース
                            fm_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL | re.MULTILINE)
                            name = entry.name
                            description = "説明はありません。"
                            
                            if fm_match:
                                fm_text = fm_match.group(1)
                                name_line = re.search(r'^name\s*:\s*(.*?)\s*$', fm_text, re.MULTILINE)
                                desc_line = re.search(r'^description\s*:\s*(.*?)\s*$', fm_text, re.MULTILINE)
                                if name_line:
                                    name = name_line.group(1).strip(" '\"")
                                if desc_line:
                                    description = desc_line.group(1).strip(" '\"")
                            
                            skills_list.append({
                                "id": entry.name,
                                "name": name,
                                "description": description
                            })
                            
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(skills_list, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif self.path.startswith('/get-skill?'):
            try:
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                skill_id = query_params.get('name', [''])[0]
                
                if not skill_id:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Skill name is required"}')
                    return
                
                skills_dir = "/opt/colab-gguf-chat/skills" if os.path.exists("/opt/colab-gguf-chat") else "./skills"
                safe_dir = os.path.abspath(skills_dir)
                skill_md_path = os.path.abspath(os.path.join(safe_dir, skill_id, "SKILL.md"))
                
                if not skill_md_path.startswith(safe_dir) or not os.path.exists(skill_md_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Skill '{skill_id}' not found"}).encode('utf-8'))
                    return
                
                with open(skill_md_path, "r", encoding="utf-8") as sf:
                    content = sf.read()
                
                import re
                body_content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL | re.MULTILINE)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body_content.encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
            
        # それ以外のリクエストは通常通り静的ファイル (index.html等) を配信
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        # 認証チェック
        if not self.check_auth():
            self.send_response(401)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"error": "Unauthorized"}')
            return

        if self.path == '/run-command':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                command = req_json.get('command', '')

                if not command:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Command is empty"}')
                    return

                print(f"[Python Server] コマンドを実行します: {command}", flush=True)

                import subprocess
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd="/opt/colab-gguf-chat" if os.path.exists("/opt/colab-gguf-chat") else "."
                )

                response_data = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except subprocess.TimeoutExpired:
                self.send_response(504)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error": "Command execution timed out after 15 seconds"}')
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                err_msg = {"error": str(e)}
                self.wfile.write(json.dumps(err_msg).encode('utf-8'))
            return
            
        elif self.path == '/save-history':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                thread_id = req_json.get('id', '')
                messages = req_json.get('messages', [])

                if not thread_id:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Thread ID is empty"}')
                    return

                history_path = "/opt/colab-gguf-chat/chat_history.json" if os.path.exists("/opt/colab-gguf-chat") else "./chat_history.json"
                history_data = []
                if os.path.exists(history_path):
                    try:
                        with open(history_path, "r", encoding="utf-8") as hf:
                            history_data = json.load(hf)
                    except Exception as parse_err:
                        print(f"[Python Server] 履歴ファイル破損のため初期化します: {parse_err}", flush=True)
                        history_data = []
                
                # 既存スレッドの更新、または新規追加
                import datetime
                timestamp = datetime.datetime.now().isoformat()
                
                thread_found = False
                for thread in history_data:
                    if thread.get("id") == thread_id:
                        thread["messages"] = messages
                        thread["timestamp"] = timestamp
                        thread_found = True
                        break
                
                if not thread_found:
                    history_data.append({
                        "id": thread_id,
                        "timestamp": timestamp,
                        "messages": messages
                    })
                
                # ファイルに書き込み
                with open(history_path, "w", encoding="utf-8") as hf:
                    json.dump(history_data, hf, ensure_ascii=False, indent=2)
                
                print(f"[Python Server] 会話履歴を保存しました。スレッドID: {thread_id}", flush=True)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                err_msg = {"error": str(e)}
                self.wfile.write(json.dumps(err_msg).encode('utf-8'))
            return

        elif self.path == '/read-file':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                file_path = req_json.get('path', '')

                if not file_path:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Path is empty"}')
                    return

                safe_path = get_safe_path(file_path)
                print(f"[Python Server] ファイルを読み取ります: {safe_path}", flush=True)

                if not os.path.exists(safe_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "File not found"}')
                    return

                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                response_data = {"content": content}
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except PermissionError as pe:
                self.send_response(403)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(pe)}).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif self.path == '/write-file':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                file_path = req_json.get('path', '')
                content = req_json.get('content', '')

                if not file_path:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Path is empty"}')
                    return

                safe_path = get_safe_path(file_path)
                print(f"[Python Server] ファイルを書き込みます: {safe_path}", flush=True)

                os.makedirs(os.path.dirname(safe_path), exist_ok=True)

                with open(safe_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')

            except PermissionError as pe:
                self.send_response(403)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(pe)}).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif self.path == '/install-skill':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                repo_url = req_json.get('url', '').strip()

                if not repo_url:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Repository URL is empty"}')
                    return

                skills_dir = "/opt/colab-gguf-chat/skills" if os.path.exists("/opt/colab-gguf-chat") else "./skills"
                os.makedirs(skills_dir, exist_ok=True)

                folder_name = repo_url.split('/')[-1].replace('.git', '')
                dest_path = os.path.join(skills_dir, folder_name)

                import subprocess
                if os.path.exists(dest_path):
                    print(f"[Python Server] スキルをアップデートします: {folder_name} (git pull)", flush=True)
                    result = subprocess.run(["git", "pull"], cwd=dest_path, capture_output=True, text=True, timeout=20)
                else:
                    print(f"[Python Server] スキルをインストールします: {folder_name} (git clone)", flush=True)
                    result = subprocess.run(["git", "clone", repo_url, dest_path], capture_output=True, text=True, timeout=20)

                if result.returncode != 0:
                    raise Exception(f"Git execution failed: {result.stderr}")

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": f"Successfully installed/updated '{folder_name}'"}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif self.path == '/proxy/chat/completions':
            try:
                # カスタムヘッダーの取得 (CORS回避のためのキーや接続先情報)
                provider = self.headers.get('X-Provider', '')
                api_key = self.headers.get('X-Api-Key', '')
                base_url = self.headers.get('X-Base-Url', '').rstrip('/')

                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_body = json.loads(post_data.decode('utf-8'))

                target_url = ""
                headers = { "Content-Type": "application/json" }

                if provider == 'claude':
                    target_url = f"{base_url}/v1/messages"
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                    headers["anthropic-dangerous-direct-browser-access"] = "true"

                    messages = req_body.get('messages', [])
                    user_msgs = [m for m in messages if m.get('role') not in ('system', 'developer')]
                    system_msg = next((m.get('content') for m in messages if m.get('role') in ('system', 'developer')), None)

                    # OpenAIの content 形式（配列オブジェクトまたはテキスト）の正規化
                    formatted_user_msgs = []
                    for m in user_msgs:
                        role = m.get('role')
                        content = m.get('content')
                        if role not in ['user', 'assistant']:
                            role = 'user'
                        
                        if isinstance(content, list):
                            claude_content = []
                            for c in content:
                                if c.get('type') == 'text':
                                    claude_content.append({ "type": "text", "text": c.get('text') })
                                elif c.get('type') == 'image_url':
                                    img_url_data = c.get('image_url', {}).get('url', '')
                                    if img_url_data.startswith('data:'):
                                        try:
                                            media_part, base64_data = img_url_data.split(';base64,')
                                            media_type = media_part.replace('data:', '')
                                            claude_content.append({
                                                "type": "image",
                                                "source": {
                                                    "type": "base64",
                                                    "media_type": media_type,
                                                    "data": base64_data
                                                }
                                            })
                                        except Exception:
                                            pass
                            formatted_user_msgs.append({ "role": role, "content": claude_content })
                        else:
                            formatted_user_msgs.append({ "role": role, "content": str(content) })

                    claude_body = {
                        "model": req_body.get('model'),
                        "messages": formatted_user_msgs,
                        "max_tokens": req_body.get('max_tokens', 2048),
                        "temperature": req_body.get('temperature', 0.5),
                        "stream": True
                    }
                    if system_msg:
                        claude_body["system"] = system_msg

                    req_data = json.dumps(claude_body).encode('utf-8')
                else:
                    target_url = f"{base_url}/chat/completions"
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    
                    # OpenAI o1/o3等の推論モデル向けのサーバーサイドパラメータ補正 (ブラウザキャッシュ未クリア対策)
                    try:
                        req_body = json.loads(post_data.decode('utf-8'))
                        model_name = req_body.get('model', '').lower()
                        import re
                        if model_name and re.search(r'(^|[\/-])(o[13]|gpt-5)([-.]|$)', model_name):
                            # max_tokens を max_completion_tokens に変換
                            if 'max_tokens' in req_body:
                                req_body['max_completion_tokens'] = req_body.pop('max_tokens')
                            # temperature を除外
                            if 'temperature' in req_body:
                                req_body.pop('temperature')
                            req_data = json.dumps(req_body).encode('utf-8')
                        else:
                            req_data = post_data
                    except Exception as pe_err:
                        print(f"[Python Server Error] パラメータ補正失敗: {pe_err}", flush=True)
                        req_data = post_data

                # HTTPリクエストの送信
                print(f"[Python Server] 外部APIへプロキシ中継します: {target_url} (プロバイダ: {provider})", flush=True)
                try:
                    debug_body = json.loads(req_data.decode('utf-8'))
                    print(f"[Python Server Debug] 送信モデル: {debug_body.get('model')}, キー接頭辞: {api_key[:10] if api_key else 'None'}...", flush=True)
                    
                    # 有効スキルがシステムプロンプトに含まれているかチェックしてログ出力
                    messages = debug_body.get('messages', [])
                    system_msg = next((m.get('content') for m in messages if m.get('role') in ('system', 'developer')), None)
                    if system_msg and "=== 有効化されたAIスキル指示 ===" in system_msg:
                        import re
                        skills = re.findall(r'【スキル: (.*?)】', system_msg)
                        print(f"[Python Server Debug] 送信メッセージに結合されたAIスキル: {skills}", flush=True)
                except Exception:
                    pass

                req = urllib.request.Request(
                    target_url,
                    data=req_data,
                    headers=headers,
                    method='POST'
                )

                with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    while True:
                        chunk = response.readline()
                        if not chunk:
                            break

                        # 生データ受信デバッグ
                        try:
                            decoded_line = chunk.decode('utf-8', errors='ignore').strip()
                            if decoded_line:
                                print(f"[Python Server Stream Debug] 受信行: {decoded_line}", flush=True)
                        except Exception:
                            pass
                        
                        if provider == 'claude':
                            line = chunk.decode('utf-8').strip()
                            if line.startswith('data:'):
                                data_str = line[5:].strip()
                                if data_str and data_str != '[DONE]':
                                    try:
                                        parsed = json.loads(data_str)
                                        # Claude の text_delta を OpenAI 規格の delta.content に変換
                                        if parsed.get('type') == 'content_block_delta' and parsed.get('delta', {}).get('text'):
                                            text_delta = parsed['delta']['text']
                                            openai_compat = {
                                                "choices": [{
                                                    "delta": {
                                                        "content": text_delta
                                                    }
                                                }]
                                            }
                                            compat_line = f"data: {json.dumps(openai_compat, ensure_ascii=False)}\n\n"
                                            self.wfile.write(compat_line.encode('utf-8'))
                                            self.wfile.flush()
                                    except Exception:
                                        pass
                        else:
                            # OpenAI互換はそのまま垂れ流す
                            self.wfile.write(chunk)
                            self.wfile.flush()

            except urllib.error.HTTPError as he:
                err_body = he.read().decode('utf-8', errors='ignore')
                print(f"[Python Server Proxy Error] HTTP {he.code}: {he.reason}\nResponse Body: {err_body}", flush=True)
                self.send_response(he.code if he.code else 500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"API Error ({he.code}): {err_body}"}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

    def init_default_skills(self, skills_dir):
        # 1. implementation-debug-logging
        log_dir = os.path.join(skills_dir, "implementation-debug-logging")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("""---
name: implementation-debug-logging
description: "自動デバッグログの埋め込み。コード変更時に進行状況や変数の状態を詳細に出力するログを自動的に挟み込みます。"
---

# implementation-debug-logging

## 指示
- あなたがプログラムコードを修正・作成する際、必ず実行フローの要所（関数の開始、終了、エラーキャッチ、条件分岐など）に、進行状況や変数の内容をダンプするデバッグログ（console.log や print 等、言語に適した方法）を明示的に挟み込んでください。
- ログのプレフィックスには `[Debug]` を付与してください。
""")

        # 2. code-review
        review_dir = os.path.join(skills_dir, "code-review")
        os.makedirs(review_dir, exist_ok=True)
        with open(os.path.join(review_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("""---
name: code-review
description: "自動コードレビュー。記述されたコードに対し、バグ、パフォーマンス、セキュリティ面での懸念点を検出し、レビューを提示します。"
---

# code-review

## 指示
- 提供されたソースコードを詳細にレビューしてください。
- レビュー観点：
  1. 構文エラーやロジックバグの有無
  2. メモリリークや非効率なループなどのパフォーマンス上の懸念
  3. SQLインジェクションやXSS、例外処理の漏れなどのセキュリティ上の欠陥
- 指摘事項はマークダウン形式のリストで簡潔に出力してください。
""")
        
    def search_searxng(self, query):
        # Python側から直接DuckDuckGo(HTML版)をスクレイピングして結果を取得
        # (CORS制限は絶対に受けず、SearXNGのような不安定さもありません)
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        print(f"[Python Server] DuckDuckGoを検索中: {search_url}", flush=True)
        
        try:
            req = urllib.request.Request(
                search_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            # SSL検証をバイパスしてフェッチ
            with urllib.request.urlopen(req, timeout=6, context=ssl_context) as response:
                html = response.read().decode('utf-8')
                
            import re
            # クラス名に result__body を含む div で大まかに分割 (HTML構造のネスト変化に非常に強い)
            parts = re.split(r'<div class="[^"]*result__body[^"]*">', html)
            mapped = []
            
            # 最初のパーツは result__body より前のヘッダー部分なので捨てる
            for part in parts[1:5]:
                # タイトルとリンク
                title_match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', part, re.DOTALL)
                # スニペット
                snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', part, re.DOTALL)
                
                if title_match and snippet_match:
                    url = title_match.group(1)
                    title = re.sub(r'<[^>]*>', '', title_match.group(2)).strip()
                    snippet = re.sub(r'<[^>]*>', '', snippet_match.group(1)).strip()
                    
                    # 転送用パラメータのデコード
                    if 'uddg=' in url:
                        url = urllib.parse.unquote(url.split('uddg=')[1].split('&')[0])
                    elif url.startswith('//'):
                        url = 'https:' + url
                        
                    mapped.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            
            if mapped:
                print(f"[Python Server] 検索成功！ {len(mapped)}件の結果を取得", flush=True)
                return mapped
                
        except Exception as e:
            print(f"[Python Server] DuckDuckGoのフェッチに失敗: {e}", flush=True)
            
        print("[Python Server] 検索結果の取得に失敗しました。", flush=True)
        return []

# サーバー起動 (ポート 8001)
handler = CustomHandler
# アドレスを再利用できるように設定 (ソケット占有エラー対策)
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
    print(f"Server started at http://localhost:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped.", flush=True)
