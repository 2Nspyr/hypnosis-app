#!/usr/bin/env python3
"""
Hypnosis & Meditation Studio — Single-File Server
Brenda Johnston | brenda-johnston.onrender.com
"""

import hashlib
import http.cookies
import http.server
import json
import mimetypes
import os
import secrets
import shutil
import urllib.parse
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#  ★  CHANGE YOUR PASSWORD HERE  ★
# ─────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "db.json"
UPLOADS_DIR = BASE_DIR / "uploads"
SESSIONS: set = set()

# ─────────────────────────────────────────────────────────────
#  HTML Pages
# ─────────────────────────────────────────────────────────────

LOGIN_HTML = """ + repr(LOGIN_HTML) + """

ADMIN_HTML = """ + repr(ADMIN_HTML) + """

PLAYER_HTML = """ + repr(PLAYER_HTML) + """

NOT_FOUND_HTML = """ + repr(NOT_FOUND_HTML) + """

# ─────────────────────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────────────────────
def load_db():
    if not DATA_FILE.exists():
        return {"tracks": [], "playlists": [], "clients": []}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_db(db):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=2)

def new_id():
    return secrets.token_hex(8)


# ─────────────────────────────────────────────────────────────
#  Request Handler
# ─────────────────────────────────────────────────────────────
class HypnosisHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg, status=400):
        self.send_json({"error": msg}, status)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def get_session_token(self):
        raw = self.headers.get("Cookie", "")
        cookies = http.cookies.SimpleCookie(raw)
        m = cookies.get("session")
        return m.value if m else None

    def is_authenticated(self):
        return self.get_session_token() in SESSIONS

    def require_auth(self):
        if not self.is_authenticated():
            self.send_error_json("Unauthorized", 401)
            return False
        return True

    # ── GET ─────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path in ("/", "/admin"):
            if self.is_authenticated():
                self.send_html(ADMIN_HTML)
            else:
                self.send_html(LOGIN_HTML)
            return

        if path.startswith("/listen/"):
            token = path[len("/listen/"):]
            db = load_db()
            client = next((c for c in db["clients"] if c["token"] == token), None)
            if not client:
                self.send_html(NOT_FOUND_HTML, 404)
                return
            self.send_html(PLAYER_HTML)
            return

        if path.startswith("/uploads/"):
            filename = urllib.parse.unquote(path[len("/uploads/"):])
            file_path = UPLOADS_DIR / filename
            if file_path.exists() and file_path.parent.resolve() == UPLOADS_DIR.resolve():
                self.serve_audio(file_path)
            else:
                self.send_response(404); self.end_headers()
            return

        if path.startswith("/api/"):
            self.handle_api_get(path)
            return

        self.send_response(404); self.end_headers()

    def serve_audio(self, file_path):
        size = file_path.stat().st_size
        range_header = self.headers.get("Range")
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "audio/mpeg"

        if range_header:
            byte_range = range_header.strip().replace("bytes=", "")
            parts = byte_range.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else size - 1
            end = min(end, size - 1)
            length = end - start + 1
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(length)
            self.send_response(206)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", length)
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", size)
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(file_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

    def handle_api_get(self, path):
        if path == "/api/tracks":
            if not self.require_auth(): return
            self.send_json(load_db()["tracks"])
        elif path == "/api/playlists":
            if not self.require_auth(): return
            self.send_json(load_db()["playlists"])
        elif path == "/api/clients":
            if not self.require_auth(): return
            self.send_json(load_db()["clients"])
        elif path.startswith("/api/client/"):
            token = path[len("/api/client/"):]
            db = load_db()
            client = next((c for c in db["clients"] if c["token"] == token), None)
            if not client:
                self.send_error_json("Not found", 404); return
            playlist = next((p for p in db["playlists"] if p["id"] == client["playlistId"]), None)
            if not playlist:
                self.send_error_json("Playlist not found", 404); return
            track_map = {t["id"]: t for t in db["tracks"]}
            tracks = [track_map[tid] for tid in playlist.get("trackIds", []) if tid in track_map]
            self.send_json({"clientName": client["name"], "playlistName": playlist["name"], "tracks": tracks})
        else:
            self.send_error_json("Not found", 404)

    # ── POST ────────────────────────────────────────────────

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path == "/api/login": self.handle_login()
        elif path == "/api/logout": self.handle_logout()
        elif path == "/api/upload":
            if not self.require_auth(): return
            self.handle_upload()
        elif path == "/api/playlists":
            if not self.require_auth(): return
            self.handle_create_playlist()
        elif path == "/api/clients":
            if not self.require_auth(): return
            self.handle_create_client()
        else:
            self.send_error_json("Not found", 404)

    # ── PUT ─────────────────────────────────────────────────

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path.startswith("/api/playlists/"):
            if not self.require_auth(): return
            self.handle_update_playlist(path[len("/api/playlists/"):])
        else:
            self.send_error_json("Not found", 404)

    # ── DELETE ──────────────────────────────────────────────

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if path.startswith("/api/tracks/"):
            if not self.require_auth(): return
            self.handle_delete_track(path[len("/api/tracks/"):])
        elif path.startswith("/api/playlists/"):
            if not self.require_auth(): return
            self.handle_delete_playlist(path[len("/api/playlists/"):])
        elif path.startswith("/api/clients/"):
            if not self.require_auth(): return
            self.handle_delete_client(path[len("/api/clients/"):])
        else:
            self.send_error_json("Not found", 404)

    # ── Handlers ────────────────────────────────────────────

    def handle_login(self):
        body = self.read_json_body()
        expected = hashlib.sha256(ADMIN_PASSWORD.encode()).digest()
        given = hashlib.sha256(body.get("password", "").encode()).digest()
        if secrets.compare_digest(expected, given):
            token = secrets.token_urlsafe(32)
            SESSIONS.add(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"session={token}; HttpOnly; Path=/; SameSite=Strict")
            b = json.dumps({"ok": True}).encode()
            self.send_header("Content-Length", len(b))
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_error_json("Invalid password", 401)

    def handle_logout(self):
        SESSIONS.discard(self.get_session_token())
        self.send_response(200)
        self.send_header("Set-Cookie", "session=; HttpOnly; Path=/; Max-Age=0")
        b = json.dumps({"ok": True}).encode()
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def parse_multipart(self):
        """Parse multipart/form-data without the deprecated cgi module."""
        ct = self.headers.get("Content-Type", "")
        boundary = None
        for part in ct.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part[9:].strip().strip('"').encode()
                break
        if not boundary:
            return {}
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        fields = {}
        delimiter = b"--" + boundary
        parts = body.split(delimiter)
        for part in parts[1:]:
            if part.startswith(b"--"):
                break
            if part.startswith(b"\r\n"):
                part = part[2:]
            if b"\r\n\r\n" not in part:
                continue
            headers_raw, content = part.split(b"\r\n\r\n", 1)
            if content.endswith(b"\r\n"):
                content = content[:-2]
            headers = {}
            for line in headers_raw.decode("utf-8", errors="replace").split("\r\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            disposition = headers.get("content-disposition", "")
            name = None
            filename = None
            for item in disposition.split(";"):
                item = item.strip()
                if item.startswith("name="):
                    name = item[5:].strip('"')
                elif item.startswith("filename="):
                    filename = item[9:].strip('"')
            if name:
                fields[name] = {"content": content, "filename": filename}
        return fields

    def handle_upload(self):
        ct = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ct:
            self.send_error_json("Expected multipart/form-data"); return
        fields = self.parse_multipart()
        if "file" not in fields:
            self.send_error_json("No file field"); return
        file_field = fields["file"]
        original = file_field.get("filename") or "track.mp3"
        safe = "".join(c for c in original if c.isalnum() or c in "._- ")
        base, ext = os.path.splitext(safe)
        unique = f"{base}_{new_id()}{ext}"
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dest = UPLOADS_DIR / unique
        with open(dest, "wb") as f:
            f.write(file_field["content"])
        title_field = fields.get("title", {})
        title = (title_field.get("content", b"").decode("utf-8", errors="replace").strip()) or base
        db = load_db()
        track = {"id": new_id(), "title": title, "filename": unique, "url": f"/uploads/{unique}", "size": dest.stat().st_size}
        db["tracks"].append(track)
        save_db(db)
        self.send_json(track, 201)

    def handle_create_playlist(self):
        body = self.read_json_body()
        name = body.get("name", "").strip()
        if not name:
            self.send_error_json("Name required"); return
        db = load_db()
        pl = {"id": new_id(), "name": name, "trackIds": body.get("trackIds", [])}
        db["playlists"].append(pl)
        save_db(db)
        self.send_json(pl, 201)

    def handle_update_playlist(self, pid):
        body = self.read_json_body()
        db = load_db()
        pl = next((p for p in db["playlists"] if p["id"] == pid), None)
        if not pl:
            self.send_error_json("Not found", 404); return
        if "name" in body: pl["name"] = body["name"].strip()
        if "trackIds" in body: pl["trackIds"] = body["trackIds"]
        save_db(db)
        self.send_json(pl)

    def handle_delete_playlist(self, pid):
        db = load_db()
        db["playlists"] = [p for p in db["playlists"] if p["id"] != pid]
        db["clients"] = [c for c in db["clients"] if c["playlistId"] != pid]
        save_db(db)
        self.send_json({"ok": True})

    def handle_create_client(self):
        body = self.read_json_body()
        name = body.get("name", "").strip()
        playlist_id = body.get("playlistId", "").strip()
        if not name or not playlist_id:
            self.send_error_json("name and playlistId required"); return
        db = load_db()
        if not any(p["id"] == playlist_id for p in db["playlists"]):
            self.send_error_json("Playlist not found", 404); return
        token = secrets.token_urlsafe(24)
        client = {"id": new_id(), "name": name, "playlistId": playlist_id, "token": token}
        db["clients"].append(client)
        save_db(db)
        self.send_json(client, 201)

    def handle_delete_client(self, cid):
        db = load_db()
        db["clients"] = [c for c in db["clients"] if c["id"] != cid]
        save_db(db)
        self.send_json({"ok": True})

    def handle_delete_track(self, tid):
        db = load_db()
        track = next((t for t in db["tracks"] if t["id"] == tid), None)
        if track:
            fp = UPLOADS_DIR / track["filename"]
            if fp.exists(): fp.unlink()
            db["tracks"] = [t for t in db["tracks"] if t["id"] != tid]
            for p in db["playlists"]:
                p["trackIds"] = [i for i in p.get("trackIds", []) if i != tid]
        save_db(db)
        self.send_json({"ok": True})


# ─────────────────────────────────────────────────────────────
#  Start server
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"""
  ╔══════════════════════════════════════════╗
  ║    Hypnosis Studio is running!           ║
  ║    Open: http://localhost:{PORT:<16}║
  ╚══════════════════════════════════════════╝
""")
    server = http.server.HTTPServer(("0.0.0.0", PORT), HypnosisHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
