import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import ssl
import traceback
import os
import sqlite3
import re

PORT = int(os.environ.get("PORT", 10200))

# SSL証明書検証をスキップするコンテキストを作成 (SSL検証エラー回避用)
ssl_context = ssl._create_unverified_context()

BASE_DIR = os.path.abspath("/opt/colab-gguf-chat" if os.path.exists("/opt/colab-gguf-chat") else ".")
DB_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "app.db")
MAX_SQL_ROWS = 100
BLOCKED_SQL_KEYWORDS = ("ATTACH", "DETACH", "LOAD_EXTENSION")

def get_safe_path(relative_path):
    normalized_rel = os.path.normpath(relative_path.replace('\x00', ''))
    target_abs = os.path.abspath(os.path.join(BASE_DIR, normalized_rel))
    if not target_abs.startswith(BASE_DIR):
        raise PermissionError("Access denied: path is outside the workspace.")
    return target_abs

def get_safe_db_path(relative_path=None):
    return get_safe_path(relative_path or "data/app.db")

def init_default_db():
    os.makedirs(DB_DIR, exist_ok=True)
    if os.path.exists(DEFAULT_DB_PATH):
        return
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    finally:
        conn.close()

def validate_sql(sql):
    sql = sql.strip()
    if not sql:
        raise ValueError("SQL is empty")
    if ";" in sql.rstrip(";"):
        raise ValueError("Multiple SQL statements are not allowed")
    upper = re.sub(r"'[^']*'", "", sql.upper())
    upper = re.sub(r'"[^"]*"', "", upper)
    for keyword in BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            raise PermissionError(f"'{keyword}' is not allowed")
    return sql

def execute_sql(db_path, sql):
    sql = validate_sql(sql)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        sql_upper = sql.lstrip().upper()
        if sql_upper.startswith(("SELECT", "PRAGMA", "WITH", "EXPLAIN")):
            rows = cursor.fetchmany(MAX_SQL_ROWS + 1)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            truncated = len(rows) > MAX_SQL_ROWS
            if truncated:
                rows = rows[:MAX_SQL_ROWS]
            return {
                "type": "query",
                "columns": columns,
                "rows": [dict(row) for row in rows],
                "row_count": len(rows),
                "truncated": truncated,
            }
        conn.commit()
        return {
            "type": "execute",
            "rows_affected": cursor.rowcount,
            "last_row_id": cursor.lastrowid,
        }
    finally:
        conn.close()

def list_tables(db_path):
    if not os.path.exists(db_path):
        return {"tables": []}
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return {"tables": [row[0] for row in cursor.fetchall()]}
    finally:
        conn.close()

def send_json_response(handler, status_code, payload):
    handler.send_response(status_code)
    handler.send_header("Content-type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # 検索中継API
        if self.path.startswith('/search?'):
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
            
        # それ以外のリクエストは通常通り静的ファイル (index.html等) を配信
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
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

        elif self.path == '/run-sql':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                sql = req_json.get('sql', '')
                db_path = get_safe_db_path(req_json.get('db'))

                print(f"[Python Server] SQLを実行します ({db_path}): {sql}", flush=True)
                result = execute_sql(db_path, sql)
                send_json_response(self, 200, result)
            except PermissionError as pe:
                send_json_response(self, 403, {"error": str(pe)})
            except ValueError as ve:
                send_json_response(self, 400, {"error": str(ve)})
            except sqlite3.Error as se:
                send_json_response(self, 400, {"error": f"SQL error: {se}"})
            except Exception as e:
                traceback.print_exc()
                send_json_response(self, 500, {"error": str(e)})
            return

        elif self.path == '/list-tables':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                req_json = json.loads(post_data.decode('utf-8'))
                db_path = get_safe_db_path(req_json.get('db'))

                print(f"[Python Server] テーブル一覧を取得します: {db_path}", flush=True)
                result = list_tables(db_path)
                send_json_response(self, 200, result)
            except PermissionError as pe:
                send_json_response(self, 403, {"error": str(pe)})
            except Exception as e:
                traceback.print_exc()
                send_json_response(self, 500, {"error": str(e)})
            return
        
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

init_default_db()

# サーバー起動
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
