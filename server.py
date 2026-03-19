#!/usr/bin/env python3
"""
Hypnosis Studio — Single-File Server
Everything is in this one file. No installation needed.
Just upload this file to GitHub and deploy on Render.com.

To change your admin password, find ADMIN_PASSWORD below and update it,
OR set an environment variable called ADMIN_PASSWORD on your hosting service.
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
#  HTML Pages (embedded directly in this file)
# ─────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #1a0533 0%, #2d1052 50%, #1a0533 100%);
    font-family: 'Georgia', serif;
  }
  .card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 24px;
    padding: 48px 40px;
    width: 100%;
    max-width: 400px;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .logo {
    width: 64px; height: 64px;
    background: linear-gradient(135deg, #c084fc, #818cf8);
    border-radius: 50%;
    margin: 0 auto 24px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px;
  }
  h1 { color: #f3e8ff; font-size: 1.6rem; font-weight: normal; margin-bottom: 6px; }
  p { color: #a78bfa; font-size: 0.9rem; margin-bottom: 32px; }
  input[type="password"] {
    width: 100%; padding: 14px 18px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 12px; color: #f3e8ff; font-size: 1rem;
    outline: none; transition: border-color 0.2s; margin-bottom: 16px;
  }
  input[type="password"]:focus { border-color: #c084fc; }
  input[type="password"]::placeholder { color: rgba(255,255,255,0.35); }
  button {
    width: 100%; padding: 14px;
    background: linear-gradient(135deg, #9333ea, #6366f1);
    border: none; border-radius: 12px; color: white;
    font-size: 1rem; font-family: 'Georgia', serif;
    cursor: pointer; transition: opacity 0.2s, transform 0.1s;
  }
  button:hover { opacity: 0.9; }
  button:active { transform: scale(0.98); }
  .error { color: #f87171; font-size: 0.85rem; margin-top: 12px; display: none; }
</style>
</head>
<body>
<div class="card">
  <div class="logo">&#127769;</div>
  <h1>Hypnosis Studio</h1>
  <p>Admin Portal</p>
  <input type="password" id="pwd" placeholder="Enter your password" autofocus>
  <button onclick="login()">Sign In</button>
  <div class="error" id="err">Incorrect password. Please try again.</div>
</div>
<script>
  document.getElementById('pwd').addEventListener('keydown', e => {
    if (e.key === 'Enter') login();
  });
  async function login() {
    const pwd = document.getElementById('pwd').value;
    const err = document.getElementById('err');
    err.style.display = 'none';
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ password: pwd })
    });
    if (res.ok) { window.location.href = '/admin'; }
    else { err.style.display = 'block'; document.getElementById('pwd').value = ''; }
  }
</script>
</body>
</html>"""

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hypnosis Studio &mdash; Admin</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f0520; --surface: #1c0b38; --surface2: #271048;
    --border: rgba(255,255,255,0.1); --purple: #a855f7;
    --purple-light: #c084fc; --text: #f3e8ff; --muted: #a78bfa;
  }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }
  .layout { display: flex; min-height: 100vh; }
  .sidebar {
    width: 220px; background: var(--surface); border-right: 1px solid var(--border);
    padding: 32px 20px; display: flex; flex-direction: column; gap: 8px;
    position: fixed; top: 0; bottom: 0; left: 0;
  }
  .sidebar-logo { font-size: 1.2rem; font-weight: 600; color: var(--purple-light); margin-bottom: 24px; padding-left: 8px; }
  .nav-btn {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border-radius: 10px; cursor: pointer; color: var(--muted); font-size: 0.9rem;
    transition: all 0.15s; border: none; background: none; width: 100%; text-align: left;
  }
  .nav-btn:hover { background: rgba(168,85,247,0.15); color: var(--text); }
  .nav-btn.active { background: rgba(168,85,247,0.25); color: var(--purple-light); }
  .nav-spacer { flex: 1; }
  .logout-btn {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border-radius: 10px; cursor: pointer; color: #f87171; font-size: 0.9rem;
    border: none; background: none; width: 100%; text-align: left; transition: background 0.15s;
  }
  .logout-btn:hover { background: rgba(239,68,68,0.15); }
  .main { margin-left: 220px; padding: 40px; flex: 1; max-width: 1100px; }
  .page { display: none; }
  .page.active { display: block; }
  h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 6px; }
  .page-desc { color: var(--muted); font-size: 0.9rem; margin-bottom: 28px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
  .upload-zone {
    border: 2px dashed rgba(168,85,247,0.4); border-radius: 14px; padding: 40px;
    text-align: center; cursor: pointer; transition: all 0.2s; background: rgba(168,85,247,0.04);
  }
  .upload-zone:hover, .upload-zone.drag-over { border-color: var(--purple); background: rgba(168,85,247,0.1); }
  .upload-zone input[type="file"] { display: none; }
  .upload-icon { font-size: 2.5rem; margin-bottom: 12px; }
  .upload-zone p { color: var(--muted); font-size: 0.9rem; }
  .upload-zone strong { color: var(--purple-light); }
  .field-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
  label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
  input[type="text"], select {
    background: var(--surface2); border: 1px solid var(--border); border-radius: 10px;
    padding: 10px 14px; color: var(--text); font-size: 0.95rem; outline: none;
    transition: border-color 0.2s; width: 100%;
  }
  input[type="text"]:focus, select:focus { border-color: var(--purple); }
  input::placeholder { color: rgba(255,255,255,0.3); }
  .btn {
    padding: 10px 20px; border-radius: 10px; border: none; font-size: 0.9rem;
    cursor: pointer; transition: opacity 0.2s, transform 0.1s;
    display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;
  }
  .btn:active { transform: scale(0.97); }
  .btn-primary { background: linear-gradient(135deg, #9333ea, #6366f1); color: white; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-ghost { background: rgba(255,255,255,0.08); color: var(--text); }
  .btn-ghost:hover { background: rgba(255,255,255,0.14); }
  .btn-danger { background: rgba(239,68,68,0.15); color: #f87171; }
  .btn-danger:hover { background: rgba(239,68,68,0.25); }
  .btn-sm { padding: 6px 12px; font-size: 0.8rem; }
  .track-list { display: flex; flex-direction: column; gap: 10px; }
  .track-item {
    display: flex; align-items: center; gap: 14px;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 12px; padding: 14px 16px; transition: border-color 0.15s;
  }
  .track-item:hover { border-color: rgba(168,85,247,0.3); }
  .track-icon {
    width: 40px; height: 40px; background: linear-gradient(135deg, #7e22ce, #4338ca);
    border-radius: 10px; display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; flex-shrink: 0;
  }
  .track-info { flex: 1; min-width: 0; }
  .track-title { font-size: 0.95rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .track-meta { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
  .track-actions { display: flex; gap: 8px; }
  .playlist-form { display: flex; flex-direction: column; gap: 16px; }
  .playlist-tracks-builder {
    background: var(--surface2); border: 1px solid var(--border); border-radius: 12px;
    min-height: 80px; padding: 12px; display: flex; flex-direction: column; gap: 8px;
  }
  .pl-track-item {
    display: flex; align-items: center; gap: 10px;
    background: var(--surface); border-radius: 8px; padding: 8px 12px; font-size: 0.88rem;
  }
  .pl-track-item .drag-handle { cursor: grab; color: var(--muted); }
  .pl-track-item .remove { cursor: pointer; color: #f87171; margin-left: auto; font-size: 1rem; }
  .pl-empty { color: var(--muted); font-size: 0.85rem; text-align: center; padding: 16px; }
  .add-track-row { display: flex; gap: 10px; }
  .playlist-list { display: flex; flex-direction: column; gap: 10px; }
  .playlist-item {
    background: var(--surface2); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; transition: border-color 0.15s;
  }
  .playlist-item:hover { border-color: rgba(168,85,247,0.4); }
  .playlist-header { display: flex; align-items: center; justify-content: space-between; }
  .playlist-name { font-weight: 600; }
  .playlist-count { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
  .client-list { display: flex; flex-direction: column; gap: 10px; }
  .client-item {
    background: var(--surface2); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px 18px; display: flex; align-items: center; gap: 14px;
  }
  .client-avatar {
    width: 40px; height: 40px; background: linear-gradient(135deg, #6d28d9, #4f46e5);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 600; flex-shrink: 0;
  }
  .client-info { flex: 1; }
  .client-name { font-weight: 500; }
  .client-playlist { font-size: 0.8rem; color: var(--muted); margin-top: 3px; }
  .client-link { font-size: 0.78rem; color: var(--purple-light); word-break: break-all; margin-top: 4px; cursor: pointer; }
  .client-link:hover { text-decoration: underline; }
  .client-actions { display: flex; gap: 8px; }
  .empty-state { text-align: center; padding: 48px; color: var(--muted); font-size: 0.9rem; }
  .empty-state .icon { font-size: 2.5rem; margin-bottom: 12px; }
  .copy-toast {
    position: fixed; bottom: 24px; left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #1e1b4b; border: 1px solid var(--purple); color: var(--text);
    padding: 10px 20px; border-radius: 999px; font-size: 0.85rem;
    opacity: 0; transition: all 0.3s; pointer-events: none; z-index: 100;
  }
  .copy-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
  .progress-bar-wrap { background: rgba(255,255,255,0.1); border-radius: 4px; height: 4px; margin-top: 12px; display: none; }
  .progress-bar { height: 4px; background: linear-gradient(90deg, #9333ea, #6366f1); border-radius: 4px; width: 0%; transition: width 0.2s; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 800px) { .two-col { grid-template-columns: 1fr; } }
  .section-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-bottom: 12px; }
</style>
</head>
<body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-logo">&#127769; Hypnosis Studio</div>
    <button class="nav-btn active" onclick="showPage('tracks', event)">&#127925; Audio Library</button>
    <button class="nav-btn" onclick="showPage('playlists', event)">&#128203; Playlists</button>
    <button class="nav-btn" onclick="showPage('clients', event)">&#128100; Clients</button>
    <div class="nav-spacer"></div>
    <button class="logout-btn" onclick="logout()">&#128682; Sign Out</button>
  </div>
  <div class="main">
    <!-- TRACKS -->
    <div class="page active" id="page-tracks">
      <h2>Audio Library</h2>
      <p class="page-desc">Upload and manage your hypnosis recordings.</p>
      <div class="card">
        <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
          <input type="file" id="file-input" accept="audio/*" multiple onchange="handleFileSelect(this.files)">
          <div class="upload-icon">&#127925;</div>
          <p><strong>Click to upload</strong> or drag &amp; drop audio files here</p>
          <p style="margin-top:6px;">MP3, WAV, M4A, OGG and more</p>
        </div>
        <div class="progress-bar-wrap" id="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div>
      </div>
      <div class="card">
        <div class="section-label">Your Recordings</div>
        <div class="track-list" id="track-list"></div>
      </div>
    </div>
    <!-- PLAYLISTS -->
    <div class="page" id="page-playlists">
      <h2>Playlists</h2>
      <p class="page-desc">Build custom playlists from your recordings.</p>
      <div class="two-col">
        <div>
          <div class="card">
            <div class="section-label" id="form-label">Create New Playlist</div>
            <div class="playlist-form">
              <input type="text" id="pl-name" placeholder="Playlist name (e.g. Deep Sleep Program)">
              <div>
                <div class="section-label">Tracks in this playlist</div>
                <div class="playlist-tracks-builder" id="pl-tracks-builder"><div class="pl-empty">No tracks added yet</div></div>
              </div>
              <div class="add-track-row">
                <select id="pl-track-select" style="flex:1"><option value="">&#8212; Choose a track to add &#8212;</option></select>
                <button class="btn btn-ghost" onclick="addTrackToPlaylist()">+ Add</button>
              </div>
              <div style="display:flex;gap:10px">
                <button class="btn btn-primary" id="save-pl-btn" onclick="savePlaylist()">&#128190; Save Playlist</button>
                <button class="btn btn-ghost" id="cancel-pl-btn" onclick="cancelEditPlaylist()" style="display:none">Cancel</button>
              </div>
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="section-label">All Playlists</div>
            <div class="playlist-list" id="playlist-list"></div>
          </div>
        </div>
      </div>
    </div>
    <!-- CLIENTS -->
    <div class="page" id="page-clients">
      <h2>Clients</h2>
      <p class="page-desc">Create private playlist links for each client.</p>
      <div class="two-col">
        <div>
          <div class="card">
            <div class="section-label">Add New Client</div>
            <div style="display:flex;flex-direction:column;gap:14px">
              <div class="field-group">
                <label>Client Name</label>
                <input type="text" id="client-name" placeholder="e.g. Sarah Johnson">
              </div>
              <div class="field-group">
                <label>Assign Playlist</label>
                <select id="client-playlist-select"><option value="">&#8212; Choose a playlist &#8212;</option></select>
              </div>
              <button class="btn btn-primary" onclick="createClient()">&#128279; Generate Private Link</button>
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="section-label">All Clients</div>
            <div class="client-list" id="client-list"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="copy-toast" id="toast"></div>
<script>
let tracks=[], playlists=[], clients=[], editingPlaylistId=null, playlistTrackIds=[];
function showPage(name, evt) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  if(evt && evt.currentTarget) evt.currentTarget.classList.add('active');
  if(name==='playlists') renderPlaylists();
  if(name==='clients') renderClients();
}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/';}
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500);}
const dropZone=document.getElementById('drop-zone');
dropZone.addEventListener('dragover',e=>{e.preventDefault();dropZone.classList.add('drag-over');});
dropZone.addEventListener('dragleave',()=>dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop',e=>{e.preventDefault();dropZone.classList.remove('drag-over');handleFileSelect(e.dataTransfer.files);});
async function handleFileSelect(files){
  const wrap=document.getElementById('progress-wrap'),bar=document.getElementById('progress-bar');
  wrap.style.display='block';let done=0;
  for(const file of files){
    const fd=new FormData();fd.append('file',file);fd.append('title',file.name.replace(/\\.[^.]+$/,''));
    await fetch('/api/upload',{method:'POST',body:fd});done++;bar.style.width=(done/files.length*100)+'%';
  }
  setTimeout(()=>{wrap.style.display='none';bar.style.width='0';},800);await loadAll();
}
async function loadAll(){
  const [t,p,c]=await Promise.all([fetch('/api/tracks').then(r=>r.json()),fetch('/api/playlists').then(r=>r.json()),fetch('/api/clients').then(r=>r.json())]);
  tracks=t;playlists=p;clients=c;renderTracks();renderPlaylistTrackSelect();renderClientPlaylistSelect();
}
function formatBytes(b){if(b<1024*1024)return(b/1024).toFixed(0)+' KB';return(b/(1024*1024)).toFixed(1)+' MB';}
function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function renderTracks(){
  const el=document.getElementById('track-list');
  if(!tracks.length){el.innerHTML='<div class="empty-state"><div class="icon">&#127925;</div>No recordings yet. Upload your first one above!</div>';return;}
  el.innerHTML=tracks.map(t=>`<div class="track-item"><div class="track-icon">&#127925;</div><div class="track-info"><div class="track-title">${escHtml(t.title)}</div><div class="track-meta">${formatBytes(t.size)}</div></div><div class="track-actions"><audio controls src="${t.url}" style="height:32px;width:180px;outline:none"></audio><button class="btn btn-danger btn-sm" onclick="deleteTrack('${t.id}')">&#128465;</button></div></div>`).join('');
}
async function deleteTrack(id){if(!confirm('Delete this recording? It will be removed from all playlists.'))return;await fetch('/api/tracks/'+id,{method:'DELETE'});await loadAll();showToast('Recording deleted.');}
function renderPlaylistTrackSelect(){const sel=document.getElementById('pl-track-select');sel.innerHTML='<option value="">&#8212; Choose a track to add &#8212;</option>'+tracks.map(t=>`<option value="${t.id}">${escHtml(t.title)}</option>`).join('');}
function addTrackToPlaylist(){const sel=document.getElementById('pl-track-select');const id=sel.value;if(!id||playlistTrackIds.includes(id))return;playlistTrackIds.push(id);renderPlaylistBuilder();sel.value='';}
function removeFromPlaylist(id){playlistTrackIds=playlistTrackIds.filter(i=>i!==id);renderPlaylistBuilder();}
function renderPlaylistBuilder(){
  const el=document.getElementById('pl-tracks-builder');
  if(!playlistTrackIds.length){el.innerHTML='<div class="pl-empty">No tracks added yet</div>';return;}
  el.innerHTML=playlistTrackIds.map((id,idx)=>{const t=tracks.find(t=>t.id===id);return`<div class="pl-track-item"><span class="drag-handle">&#10783;</span><span>${idx+1}. ${escHtml(t?t.title:'Unknown')}</span><span class="remove" onclick="removeFromPlaylist('${id}')">&#10005;</span></div>`;}).join('');
}
async function savePlaylist(){
  const name=document.getElementById('pl-name').value.trim();
  if(!name){alert('Please enter a playlist name.');return;}
  const data={name,trackIds:playlistTrackIds};
  if(editingPlaylistId){await fetch('/api/playlists/'+editingPlaylistId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});showToast('Playlist updated!');}
  else{await fetch('/api/playlists',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});showToast('Playlist created!');}
  cancelEditPlaylist();await loadAll();renderPlaylists();
}
function editPlaylist(pl){
  editingPlaylistId=pl.id;document.getElementById('pl-name').value=pl.name;
  playlistTrackIds=[...(pl.trackIds||[])];
  document.getElementById('form-label').textContent='Edit Playlist';
  document.getElementById('save-pl-btn').textContent='&#128190; Update Playlist';
  document.getElementById('cancel-pl-btn').style.display='inline-flex';
  renderPlaylistBuilder();document.getElementById('pl-name').focus();
}
function cancelEditPlaylist(){
  editingPlaylistId=null;document.getElementById('pl-name').value='';playlistTrackIds=[];
  document.getElementById('form-label').textContent='Create New Playlist';
  document.getElementById('save-pl-btn').textContent='&#128190; Save Playlist';
  document.getElementById('cancel-pl-btn').style.display='none';renderPlaylistBuilder();
}
function renderPlaylists(){
  const el=document.getElementById('playlist-list');
  if(!playlists.length){el.innerHTML='<div class="empty-state"><div class="icon">&#128203;</div>No playlists yet. Create your first one!</div>';return;}
  el.innerHTML=playlists.map(p=>{const count=(p.trackIds||[]).length;return`<div class="playlist-item"><div class="playlist-header"><div><div class="playlist-name">${escHtml(p.name)}</div><div class="playlist-count">${count} track${count!==1?'s':''}</div></div><div style="display:flex;gap:8px"><button class="btn btn-ghost btn-sm" onclick='editPlaylist(${JSON.stringify(p)})'>&#9999;&#65039; Edit</button><button class="btn btn-danger btn-sm" onclick="deletePlaylist('${p.id}')">&#128465;</button></div></div></div>`;}).join('');
}
async function deletePlaylist(id){if(!confirm('Delete this playlist?'))return;await fetch('/api/playlists/'+id,{method:'DELETE'});await loadAll();renderPlaylists();showToast('Playlist deleted.');}
function renderClientPlaylistSelect(){const sel=document.getElementById('client-playlist-select');sel.innerHTML='<option value="">&#8212; Choose a playlist &#8212;</option>'+playlists.map(p=>`<option value="${p.id}">${escHtml(p.name)}</option>`).join('');}
function renderClients(){
  renderClientPlaylistSelect();
  const el=document.getElementById('client-list');
  if(!clients.length){el.innerHTML='<div class="empty-state"><div class="icon">&#128100;</div>No clients yet. Add your first one!</div>';return;}
  el.innerHTML=clients.map(c=>{const pl=playlists.find(p=>p.id===c.playlistId);const link=location.origin+'/listen/'+c.token;const initials=c.name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);return`<div class="client-item"><div class="client-avatar">${initials}</div><div class="client-info"><div class="client-name">${escHtml(c.name)}</div><div class="client-playlist">&#128203; ${pl?escHtml(pl.name):'Unknown'}</div><div class="client-link" onclick="copyLink('${link}')">&#128279; ${link}</div></div><div class="client-actions"><button class="btn btn-ghost btn-sm" onclick="copyLink('${link}')">&#128203; Copy</button><button class="btn btn-danger btn-sm" onclick="deleteClient('${c.id}')">&#128465;</button></div></div>`;}).join('');
}
async function createClient(){
  const name=document.getElementById('client-name').value.trim();
  const playlistId=document.getElementById('client-playlist-select').value;
  if(!name){alert('Please enter a client name.');return;}
  if(!playlistId){alert('Please select a playlist.');return;}
  const res=await fetch('/api/clients',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,playlistId})});
  const client=await res.json();
  document.getElementById('client-name').value='';document.getElementById('client-playlist-select').value='';
  await loadAll();renderClients();copyLink(location.origin+'/listen/'+client.token);showToast('Client created! Link copied to clipboard.');
}
async function deleteClient(id){if(!confirm('Remove this client?'))return;await fetch('/api/clients/'+id,{method:'DELETE'});await loadAll();renderClients();showToast('Client removed.');}
function copyLink(url){navigator.clipboard.writeText(url).then(()=>showToast('Link copied to clipboard!'));}
loadAll();
</script>
</body>
</html>"""

PLAYER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Hypnosis Program</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root { --bg:#07011a; --border:rgba(255,255,255,0.1); --purple:#a855f7; --purple-light:#c084fc; --text:#f3e8ff; --muted:#a78bfa; }
  body { background:var(--bg); color:var(--text); font-family:'Georgia','Times New Roman',serif; min-height:100vh; overflow-x:hidden; }
  .orb { position:fixed; border-radius:50%; filter:blur(80px); opacity:0.25; pointer-events:none; animation:drift 12s ease-in-out infinite; }
  .orb1 { width:500px;height:500px;background:#7e22ce;top:-100px;left:-100px;animation-delay:0s; }
  .orb2 { width:400px;height:400px;background:#4338ca;bottom:-100px;right:-80px;animation-delay:4s; }
  .orb3 { width:300px;height:300px;background:#9333ea;top:40%;left:50%;animation-delay:8s; }
  @keyframes drift{0%,100%{transform:translate(0,0) scale(1);}33%{transform:translate(30px,-20px) scale(1.05);}66%{transform:translate(-20px,30px) scale(0.95);}}
  .container { position:relative;z-index:1;max-width:680px;margin:0 auto;padding:48px 24px 80px; }
  .header { text-align:center;margin-bottom:48px; }
  .moon { font-size:2.5rem;margin-bottom:16px;animation:glow 4s ease-in-out infinite; }
  @keyframes glow{0%,100%{filter:drop-shadow(0 0 8px rgba(168,85,247,0.5));}50%{filter:drop-shadow(0 0 20px rgba(168,85,247,0.9));}}
  .greeting { color:var(--muted);font-size:0.9rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px; }
  .client-name { font-size:1.8rem;font-weight:normal; }
  .playlist-title { font-size:1rem;color:var(--muted);margin-top:6px;font-style:italic; }
  .now-playing-card { background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:24px;padding:32px;margin-bottom:28px;backdrop-filter:blur(12px);text-align:center; }
  .now-playing-label { font-size:0.72rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:20px; }
  .vinyl { width:140px;height:140px;border-radius:50%;margin:0 auto 24px;background:conic-gradient(#1e0a3c,#4c1d95,#1e0a3c,#3730a3,#1e0a3c);display:flex;align-items:center;justify-content:center;box-shadow:0 0 40px rgba(139,92,246,0.4);position:relative; }
  .vinyl.spinning { animation:spin 8s linear infinite; }
  @keyframes spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
  .vinyl-center { position:absolute;width:36px;height:36px;background:var(--bg);border-radius:50%;border:3px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;font-size:1rem; }
  .track-title-now { font-size:1.15rem;font-weight:600;margin-bottom:4px; }
  .track-index { font-size:0.8rem;color:var(--muted);margin-bottom:28px; }
  .progress-area { margin-bottom:20px; }
  .progress-track { width:100%;height:4px;background:rgba(255,255,255,0.12);border-radius:4px;cursor:pointer;margin-bottom:8px; }
  .progress-fill { height:4px;background:linear-gradient(90deg,#9333ea,#818cf8);border-radius:4px;width:0%;pointer-events:none;transition:width 0.3s linear; }
  .time-row { display:flex;justify-content:space-between;font-size:0.78rem;color:var(--muted);font-family:monospace; }
  .controls { display:flex;align-items:center;justify-content:center;gap:20px;margin-bottom:20px; }
  .ctrl-btn { background:none;border:none;color:var(--muted);cursor:pointer;font-size:1.4rem;padding:8px;border-radius:50%;transition:color 0.15s,transform 0.1s,background 0.15s;line-height:1;display:flex;align-items:center;justify-content:center; }
  .ctrl-btn:hover { color:var(--text);background:rgba(255,255,255,0.08); }
  .ctrl-btn:active { transform:scale(0.9); }
  .play-btn { width:60px;height:60px;background:linear-gradient(135deg,#9333ea,#6366f1);color:white;font-size:1.6rem;box-shadow:0 4px 20px rgba(147,51,234,0.5); }
  .play-btn:hover { opacity:0.9;color:white; }
  .volume-row { display:flex;align-items:center;gap:10px;justify-content:center;color:var(--muted);font-size:0.9rem; }
  input[type="range"] { -webkit-appearance:none;width:100px;height:4px;background:rgba(255,255,255,0.15);border-radius:4px;outline:none;cursor:pointer; }
  input[type="range"]::-webkit-slider-thumb { -webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:var(--purple-light);cursor:pointer; }
  .playlist-header-row { display:flex;justify-content:space-between;align-items:center;margin-bottom:14px; }
  .playlist-heading { font-size:0.75rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted); }
  .track-count-badge { background:rgba(168,85,247,0.15);color:var(--purple-light);border-radius:6px;padding:2px 8px;font-size:0.72rem; }
  .playlist-items { display:flex;flex-direction:column;gap:8px; }
  .playlist-track { display:flex;align-items:center;gap:14px;background:rgba(255,255,255,0.04);border:1px solid transparent;border-radius:14px;padding:14px 16px;cursor:pointer;transition:all 0.2s; }
  .playlist-track:hover { background:rgba(255,255,255,0.07);border-color:rgba(168,85,247,0.2); }
  .playlist-track.active { background:rgba(147,51,234,0.15);border-color:rgba(147,51,234,0.5); }
  .track-num { width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.08);display:flex;align-items:center;justify-content:center;font-size:0.75rem;color:var(--muted);flex-shrink:0;font-family:monospace; }
  .playlist-track.active .track-num { background:var(--purple);color:white; }
  .track-num-icon { display:none; }
  .playlist-track.active .track-num-icon { display:block;font-size:0.85rem; }
  .playlist-track.active .track-num-num { display:none; }
  .pt-info { flex:1;min-width:0; }
  .pt-title { font-size:0.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
  .pt-dur { font-size:0.75rem;color:var(--muted);margin-top:2px;font-family:monospace; }
  .playlist-track.active .pt-title { color:var(--purple-light); }
  .footer { text-align:center;margin-top:48px;color:rgba(167,139,250,0.4);font-size:0.78rem; }
  .loading-screen { position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:var(--bg);z-index:999;flex-direction:column;gap:16px;color:var(--muted); }
  .spinner { width:40px;height:40px;border:3px solid rgba(168,85,247,0.2);border-top-color:var(--purple);border-radius:50%;animation:spin 0.8s linear infinite; }
  .not-found { text-align:center;padding:80px 24px; }
  .not-found .icon { font-size:3rem;margin-bottom:16px; }
  .not-found h2 { margin-bottom:8px; }
  .not-found p { color:var(--muted);font-size:0.9rem; }
</style>
</head>
<body>
<div class="orb orb1"></div><div class="orb orb2"></div><div class="orb orb3"></div>
<div class="loading-screen" id="loading"><div class="spinner"></div><div>Loading your program&hellip;</div></div>
<div class="container" id="app" style="display:none">
  <div class="header">
    <div class="moon">&#127769;</div>
    <div class="greeting">Welcome back</div>
    <div class="client-name" id="client-name">&mdash;</div>
    <div class="playlist-title" id="playlist-name">&mdash;</div>
  </div>
  <div class="now-playing-card">
    <div class="now-playing-label">Now Playing</div>
    <div class="vinyl" id="vinyl"><div class="vinyl-center">&#127769;</div></div>
    <div class="track-title-now" id="now-title">&mdash;</div>
    <div class="track-index" id="now-index">&mdash;</div>
    <div class="progress-area">
      <div class="progress-track" id="progress-track" onclick="seek(event)"><div class="progress-fill" id="progress-fill"></div></div>
      <div class="time-row"><span id="time-current">0:00</span><span id="time-total">0:00</span></div>
    </div>
    <div class="controls">
      <button class="ctrl-btn" onclick="prevTrack()" title="Previous">&#9198;</button>
      <button class="ctrl-btn" onclick="skipBack()" title="Back 15s">&#8634; 15</button>
      <button class="ctrl-btn play-btn" id="play-btn" onclick="togglePlay()">&#9654;</button>
      <button class="ctrl-btn" onclick="skipForward()" title="Forward 15s">15 &#8635;</button>
      <button class="ctrl-btn" onclick="nextTrack()" title="Next">&#9197;</button>
    </div>
    <div class="volume-row">&#128264;<input type="range" id="volume" min="0" max="1" step="0.01" value="1" oninput="setVolume(this.value)">&#128266;</div>
  </div>
  <div class="playlist-section">
    <div class="playlist-header-row">
      <div class="playlist-heading">Your Sessions</div>
      <div class="track-count-badge" id="track-badge">0 tracks</div>
    </div>
    <div class="playlist-items" id="playlist-items"></div>
  </div>
  <div class="footer">Your personal hypnosis program &middot; Listen anytime</div>
</div>
<audio id="audio"></audio>
<script>
const audio=document.getElementById('audio');
let tracks=[],currentIdx=0;
const token=location.pathname.split('/listen/')[1];
async function init(){
  try{
    const res=await fetch('/api/client/'+token);
    if(!res.ok)throw new Error();
    const data=await res.json();
    tracks=data.tracks;
    document.getElementById('client-name').textContent=data.clientName;
    document.getElementById('playlist-name').textContent=data.playlistName;
    document.getElementById('track-badge').textContent=tracks.length+' track'+(tracks.length!==1?'s':'');
    document.title=data.clientName+' \u2014 Your Hypnosis Program';
    renderPlaylist();if(tracks.length>0)loadTrack(0);
    document.getElementById('loading').style.display='none';
    document.getElementById('app').style.display='block';
  }catch(e){
    document.getElementById('loading').innerHTML='<div class="not-found"><div class="icon">&#128302;</div><h2>Link not found</h2><p>This link may be invalid or has been removed. Please contact your practitioner.</p></div>';
  }
}
function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function renderPlaylist(){
  document.getElementById('playlist-items').innerHTML=tracks.map((t,i)=>`<div class="playlist-track ${i===currentIdx?'active':''}" id="pt-${i}" onclick="loadTrack(${i});play();"><div class="track-num"><span class="track-num-icon">${i===currentIdx?'&#9834;':''}</span><span class="track-num-num">${i+1}</span></div><div class="pt-info"><div class="pt-title">${escHtml(t.title)}</div><div class="pt-dur" id="dur-${i}">&mdash;</div></div></div>`).join('');
}
function updateActiveTrack(){
  document.querySelectorAll('.playlist-track').forEach((el,i)=>{
    el.classList.toggle('active',i===currentIdx);
    const icon=el.querySelector('.track-num-icon'),num=el.querySelector('.track-num-num');
    if(icon)icon.innerHTML=i===currentIdx?'&#9834;':'';
    if(num)num.style.display=i===currentIdx?'none':'';
  });
}
function loadTrack(idx){
  if(idx<0||idx>=tracks.length)return;currentIdx=idx;
  audio.src=tracks[idx].url;audio.load();
  document.getElementById('now-title').textContent=tracks[idx].title;
  document.getElementById('now-index').textContent='Track '+(idx+1)+' of '+tracks.length;
  document.getElementById('progress-fill').style.width='0%';
  document.getElementById('time-current').textContent='0:00';
  document.getElementById('time-total').textContent='&mdash;';
  updateActiveTrack();
  const ptEl=document.getElementById('pt-'+idx);if(ptEl)ptEl.scrollIntoView({behavior:'smooth',block:'nearest'});
}
function play(){audio.play();document.getElementById('play-btn').innerHTML='&#9646;&#9646;';document.getElementById('vinyl').classList.add('spinning');}
function pause(){audio.pause();document.getElementById('play-btn').innerHTML='&#9654;';document.getElementById('vinyl').classList.remove('spinning');}
function togglePlay(){if(audio.paused)play();else pause();}
function nextTrack(){if(currentIdx<tracks.length-1){loadTrack(currentIdx+1);play();}}
function prevTrack(){if(audio.currentTime>3){audio.currentTime=0;}else if(currentIdx>0){loadTrack(currentIdx-1);play();}}
function skipForward(){audio.currentTime=Math.min(audio.currentTime+15,audio.duration||0);}
function skipBack(){audio.currentTime=Math.max(audio.currentTime-15,0);}
function setVolume(v){audio.volume=parseFloat(v);}
function seek(e){if(!audio.duration)return;const rect=e.currentTarget.getBoundingClientRect();audio.currentTime=((e.clientX-rect.left)/rect.width)*audio.duration;}
function fmt(s){if(!s||isNaN(s))return'0:00';return Math.floor(s/60)+':'+(Math.floor(s%60)).toString().padStart(2,'0');}
audio.addEventListener('timeupdate',()=>{if(!audio.duration)return;document.getElementById('progress-fill').style.width=(audio.currentTime/audio.duration*100)+'%';document.getElementById('time-current').textContent=fmt(audio.currentTime);});
audio.addEventListener('loadedmetadata',()=>{document.getElementById('time-total').textContent=fmt(audio.duration);const d=document.getElementById('dur-'+currentIdx);if(d)d.textContent=fmt(audio.duration);});
audio.addEventListener('ended',()=>{pause();if(currentIdx<tracks.length-1)nextTrack();});
audio.addEventListener('play',()=>{document.getElementById('play-btn').innerHTML='&#9646;&#9646;';document.getElementById('vinyl').classList.add('spinning');});
audio.addEventListener('pause',()=>{document.getElementById('play-btn').innerHTML='&#9654;';document.getElementById('vinyl').classList.remove('spinning');});
init();
</script>
</body>
</html>"""

NOT_FOUND_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Not Found</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#07011a;color:#f3e8ff;font-family:Georgia,serif;text-align:center}.icon{font-size:3rem;margin-bottom:16px}h2{font-size:1.4rem;font-weight:normal;margin-bottom:8px}p{color:#a78bfa;font-size:.9rem}</style>
</head><body><div><div class="icon">&#128302;</div><h2>Link not found</h2><p>This link may be invalid or has been removed.<br>Please contact your practitioner.</p></div></body></html>"""


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
