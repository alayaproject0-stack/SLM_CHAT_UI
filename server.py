import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse
import json
import ssl
import traceback
import os

PORT = int(os.environ.get("PORT", 10200))

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
                    user_msgs = [m for m in messages if m.get('role') != 'system']
                    system_msg = next((m.get('content') for m in messages if m.get('role') == 'system'), None)

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
                    req_data = post_data

                # HTTPリクエストの送信
                print(f"[Python Server] 外部APIへプロキシ中継します: {target_url} (プロバイダ: {provider})", flush=True)
                req = urllib.request.Request(
                    target_url,
                    data=req_data,
                    headers=headers,
                    method='POST'
                )

                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with urllib.request.urlopen(req, context=ssl_context) as response:
                    while True:
                        chunk = response.readline()
                        if not chunk:
                            break
                        
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
