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

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hypnosis & Meditation Studio</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  :root{--bg:#080010;--card:#110018;--pink:#ee0074;--pink-light:#ff4da6;--text:#fff0f7;--muted:#c084a0}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:var(--card);border:1px solid rgba(238,0,116,0.25);border-radius:20px;padding:48px 40px;width:100%;max-width:400px;box-shadow:0 0 60px rgba(238,0,116,0.12)}
  .logo-wrap{text-align:center;margin-bottom:32px}
  .logo-wrap img{width:160px;filter:drop-shadow(0 0 12px rgba(238,0,116,0.4))}
  .brand{text-align:center;font-size:13px;letter-spacing:0.15em;text-transform:uppercase;color:var(--muted);margin-bottom:32px}
  h1{text-align:center;font-size:22px;font-weight:300;letter-spacing:0.08em;margin-bottom:8px}
  .sub{text-align:center;color:var(--muted);font-size:13px;margin-bottom:32px}
  label{display:block;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
  input[type=password]{width:100%;background:#1c0028;border:1px solid rgba(238,0,116,0.3);border-radius:10px;color:var(--text);padding:14px 16px;font-size:15px;outline:none;transition:.2s}
  input[type=password]:focus{border-color:var(--pink);box-shadow:0 0 0 3px rgba(238,0,116,0.15)}
  button{width:100%;margin-top:20px;background:linear-gradient(135deg,#ee0074,#a8004f);border:none;border-radius:10px;color:#fff;font-size:15px;font-weight:600;letter-spacing:0.05em;padding:14px;cursor:pointer;transition:.2s;box-shadow:0 4px 20px rgba(238,0,116,0.35)}
  button:hover{transform:translateY(-1px);box-shadow:0 6px 28px rgba(238,0,116,0.5)}
  .err{color:#ff6b9e;font-size:13px;text-align:center;margin-top:14px;display:none}
  .footer{text-align:center;color:var(--muted);font-size:11px;margin-top:32px;letter-spacing:0.05em}
</style>
</head>
<body>
<div class="card">
  <div class="logo-wrap"><img src="data:image/png;base64,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" alt="Logo"></div>
  <div class="brand">Hypnosis &amp; Meditation Studio</div>
  <h1>Welcome back</h1>
  <p class="sub">Sign in to your studio</p>
  <div>
    <label for="pw">Password</label>
    <input type="password" id="pw" placeholder="Enter your password" autofocus>
    <button onclick="login()">Sign In</button>
    <div class="err" id="err">Incorrect password. Please try again.</div>
  </div>
  <div class="footer">brenda-johnston.com</div>
</div>
<script>
function login(){
  const pw=document.getElementById('pw').value;
  const err=document.getElementById('err');
  err.style.display='none';
  fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})})
    .then(r=>r.json()).then(d=>{if(d.ok)location.reload();else{err.style.display='block';}})
    .catch(()=>{err.style.display='block';});
}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')login();});
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Studio Admin — Hypnosis &amp; Meditation Studio</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#080010;--sidebar:#110018;--card:#140020;--pink:#ee0074;--pink-light:#ff4da6;--text:#fff0f7;--muted:#c084a0;--border:rgba(238,0,116,0.2)}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;display:flex;min-height:100vh}
/* Sidebar */
#sidebar{width:240px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}
.sidebar-brand{padding:24px 20px;border-bottom:1px solid var(--border)}
.sidebar-brand img{width:130px;filter:drop-shadow(0 0 8px rgba(238,0,116,0.3))}
.sidebar-brand .name{font-size:11px;letter-spacing:0.15em;text-transform:uppercase;color:var(--muted);margin-top:10px}
nav{padding:20px 0;flex:1}
nav a{display:flex;align-items:center;gap:10px;padding:12px 20px;color:var(--muted);text-decoration:none;font-size:14px;transition:.15s;cursor:pointer}
nav a:hover,nav a.active{background:rgba(238,0,116,0.1);color:var(--text);border-right:2px solid var(--pink)}
nav a svg{width:18px;height:18px;flex-shrink:0}
.sidebar-footer{padding:16px 20px;border-top:1px solid var(--border)}
.logout-btn{display:block;width:100%;background:transparent;border:1px solid var(--border);border-radius:8px;color:var(--muted);font-size:13px;padding:8px;cursor:pointer;transition:.15s;text-align:center}
.logout-btn:hover{border-color:var(--pink);color:var(--pink)}
/* Main */
#main{flex:1;padding:32px;overflow-y:auto}
.page{display:none}
.page.active{display:block}
.page-title{font-size:24px;font-weight:300;letter-spacing:0.06em;margin-bottom:8px}
.page-sub{color:var(--muted);font-size:14px;margin-bottom:28px}
/* Cards */
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:20px}
.card h3{font-size:16px;font-weight:500;margin-bottom:16px;color:var(--text)}
/* Forms */
.form-row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
input[type=text],input[type=file],select,textarea{background:#1c0028;border:1px solid var(--border);border-radius:8px;color:var(--text);padding:10px 14px;font-size:14px;outline:none;transition:.2s;font-family:inherit}
input[type=text],select{min-width:220px}
input:focus,select:focus{border-color:var(--pink);box-shadow:0 0 0 2px rgba(238,0,116,0.12)}
.btn{background:linear-gradient(135deg,#ee0074,#a8004f);border:none;border-radius:8px;color:#fff;font-size:14px;font-weight:600;padding:10px 20px;cursor:pointer;transition:.2s;box-shadow:0 3px 14px rgba(238,0,116,0.3)}
.btn:hover{transform:translateY(-1px);box-shadow:0 5px 20px rgba(238,0,116,0.45)}
.btn-sm{padding:6px 14px;font-size:13px}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--muted);box-shadow:none}
.btn-ghost:hover{border-color:var(--pink);color:var(--pink);background:rgba(238,0,116,0.05);transform:none;box-shadow:none}
.btn-danger{background:linear-gradient(135deg,#c0002e,#7a0020)}
/* Table */
.tbl{width:100%;border-collapse:collapse;font-size:14px}
.tbl th{text-align:left;color:var(--muted);font-size:12px;letter-spacing:0.08em;text-transform:uppercase;padding:8px 12px;border-bottom:1px solid var(--border)}
.tbl td{padding:12px;border-bottom:1px solid rgba(238,0,116,0.08);vertical-align:middle}
.tbl tr:last-child td{border-bottom:none}
/* Upload progress */
#upload-progress{margin-top:14px;display:none}
progress{width:100%;height:8px;border-radius:4px;overflow:hidden;-webkit-appearance:none;appearance:none}
progress::-webkit-progress-bar{background:#1c0028;border-radius:4px}
progress::-webkit-progress-value{background:linear-gradient(90deg,#ee0074,#ff4da6);border-radius:4px}
/* Link box */
.link-box{background:#0e0018;border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:13px;color:var(--muted);word-break:break-all;margin-top:8px}
.link-box a{color:var(--pink-light);text-decoration:none}
.link-box a:hover{text-decoration:underline}
/* Toast */
#toast{position:fixed;bottom:24px;right:24px;background:#1c0028;border:1px solid var(--pink);border-radius:10px;padding:12px 20px;font-size:14px;color:var(--text);display:none;z-index:999;box-shadow:0 4px 20px rgba(238,0,116,0.3)}
/* Responsive */
@media(max-width:640px){body{flex-direction:column}#sidebar{width:100%;flex-direction:row;overflow-x:auto}nav{display:flex;padding:0}nav a{padding:14px 16px}#main{padding:20px}}
/* Drag-drop */
.drop-zone{border:2px dashed rgba(238,0,116,0.35);border-radius:10px;padding:28px;text-align:center;color:var(--muted);transition:.2s;cursor:pointer}
.drop-zone.over{background:rgba(238,0,116,0.08);border-color:var(--pink)}
.drop-zone input{display:none}
</style>
</head>
<body>
<aside id="sidebar">
  <div class="sidebar-brand">
    <img src="data:image/png;base64,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" alt="Logo">
    <div class="name">Admin Studio</div>
  </div>
  <nav>
    <a class="active" onclick="showPage('library')">
      <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>
      Audio Library
    </a>
    <a onclick="showPage('playlists')">
      <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h10"/></svg>
      Playlists
    </a>
    <a onclick="showPage('clients')">
      <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
      Clients
    </a>
  </nav>
  <div class="sidebar-footer">
    <button class="logout-btn" onclick="logout()">Sign Out</button>
  </div>
</aside>

<main id="main">

  <!-- LIBRARY PAGE -->
  <div id="page-library" class="page active">
    <div class="page-title">Audio Library</div>
    <p class="page-sub">Upload and manage your hypnosis recordings</p>
    <div class="card">
      <h3>Upload Audio</h3>
      <div class="form-row">
        <input type="text" id="track-title" placeholder="Track title (optional)">
      </div>
      <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <input type="file" id="file-input" accept="audio/*">
        <p>Drop audio file here or click to browse</p>
        <p style="font-size:12px;margin-top:6px;opacity:0.6">MP3, M4A, WAV, OGG supported</p>
      </div>
      <div id="upload-progress">
        <progress id="upload-bar" value="0" max="100"></progress>
        <p id="upload-msg" style="font-size:13px;color:var(--muted);margin-top:6px"></p>
      </div>
    </div>
    <div class="card">
      <h3>All Tracks</h3>
      <div id="tracks-list"><p style="color:var(--muted);font-size:14px">Loading...</p></div>
    </div>
  </div>

  <!-- PLAYLISTS PAGE -->
  <div id="page-playlists" class="page">
    <div class="page-title">Playlists</div>
    <p class="page-sub">Group tracks into programs for your clients</p>
    <div class="card">
      <h3>Create Playlist</h3>
      <div class="form-row">
        <input type="text" id="pl-name" placeholder="Playlist name">
        <button class="btn" onclick="createPlaylist()">Create</button>
      </div>
    </div>
    <div class="card">
      <h3>All Playlists</h3>
      <div id="playlists-list"><p style="color:var(--muted);font-size:14px">Loading...</p></div>
    </div>
  </div>

  <!-- CLIENTS PAGE -->
  <div id="page-clients" class="page">
    <div class="page-title">Clients</div>
    <p class="page-sub">Create private listening links for each client</p>
    <div class="card">
      <h3>Add Client</h3>
      <div class="form-row">
        <input type="text" id="client-name" placeholder="Client name">
        <select id="client-playlist"><option value="">— select playlist —</option></select>
        <button class="btn" onclick="createClient()">Create Link</button>
      </div>
    </div>
    <div class="card">
      <h3>All Clients</h3>
      <div id="clients-list"><p style="color:var(--muted);font-size:14px">Loading...</p></div>
    </div>
  </div>

</main>
<div id="toast"></div>

<script>
const HOST = location.origin;
let allTracks=[], allPlaylists=[], allClients=[];

function showPage(p){
  document.querySelectorAll('.page').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(el=>el.classList.remove('active'));
  document.getElementById('page-'+p).classList.add('active');
  event.currentTarget.classList.add('active');
  if(p==='library')loadTracks();
  if(p==='playlists')loadPlaylists();
  if(p==='clients')loadClients();
}

function toast(msg){
  const t=document.getElementById('toast');t.textContent=msg;t.style.display='block';
  setTimeout(()=>t.style.display='none',2800);
}

function logout(){fetch('/api/logout',{method:'POST'}).then(()=>location.reload());}

// ── Tracks ──
async function loadTracks(){
  const r=await fetch('/api/tracks');allTracks=await r.json();renderTracks();
}
function renderTracks(){
  const el=document.getElementById('tracks-list');
  if(!allTracks.length){el.innerHTML='<p style="color:var(--muted);font-size:14px">No tracks yet. Upload your first recording above.</p>';return;}
  el.innerHTML='<table class="tbl"><thead><tr><th>Title</th><th>File</th><th></th></tr></thead><tbody>'+
    allTracks.map(t=>`<tr><td>${esc(t.title)}</td><td style="color:var(--muted);font-size:12px">${esc(t.filename)}</td><td style="text-align:right"><button class="btn btn-sm btn-danger" onclick="deleteTrack('${t.id}')">Delete</button></td></tr>`).join('')+
    '</tbody></table>';
}
async function deleteTrack(id){
  if(!confirm('Delete this track? It will be removed from all playlists.'))return;
  await fetch('/api/tracks/'+id,{method:'DELETE'});loadTracks();toast('Track deleted.');
}

// ── Upload ──
const dropZone=document.getElementById('drop-zone');
const fileInput=document.getElementById('file-input');
dropZone.addEventListener('dragover',e=>{e.preventDefault();dropZone.classList.add('over');});
dropZone.addEventListener('dragleave',()=>dropZone.classList.remove('over'));
dropZone.addEventListener('drop',e=>{e.preventDefault();dropZone.classList.remove('over');const f=e.dataTransfer.files[0];if(f)doUpload(f);});
fileInput.addEventListener('change',()=>{if(fileInput.files[0])doUpload(fileInput.files[0]);});

function doUpload(file){
  const title=document.getElementById('track-title').value.trim();
  const fd=new FormData();fd.append('file',file);if(title)fd.append('title',title);
  const prog=document.getElementById('upload-progress');
  const bar=document.getElementById('upload-bar');
  const msg=document.getElementById('upload-msg');
  prog.style.display='block';bar.value=0;msg.textContent='Uploading…';
  const xhr=new XMLHttpRequest();
  xhr.open('POST','/api/upload');
  xhr.upload.onprogress=e=>{if(e.lengthComputable)bar.value=Math.round(e.loaded/e.total*100);};
  xhr.onload=()=>{
    if(xhr.status===201){msg.textContent='Upload complete!';document.getElementById('track-title').value='';fileInput.value='';loadTracks();}
    else msg.textContent='Upload failed.';
    setTimeout(()=>{prog.style.display='none';},2000);
  };
  xhr.onerror=()=>{msg.textContent='Upload error.';};
  xhr.send(fd);
}

// ── Playlists ──
async function loadPlaylists(){
  const [pr,tr]=await Promise.all([fetch('/api/playlists'),fetch('/api/tracks')]);
  allPlaylists=await pr.json();allTracks=await tr.json();
  renderPlaylists();
  const sel=document.getElementById('client-playlist');
  if(sel){sel.innerHTML='<option value="">— select playlist —</option>'+allPlaylists.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');}
}
function renderPlaylists(){
  const el=document.getElementById('playlists-list');
  if(!allPlaylists.length){el.innerHTML='<p style="color:var(--muted);font-size:14px">No playlists yet.</p>';return;}
  const tMap=Object.fromEntries(allTracks.map(t=>[t.id,t]));
  el.innerHTML=allPlaylists.map(pl=>`
    <div class="card" style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <strong>${esc(pl.name)}</strong>
        <button class="btn btn-sm btn-danger" onclick="deletePlaylist('${pl.id}')">Delete</button>
      </div>
      <div style="margin-bottom:12px;font-size:13px;color:var(--muted)">${(pl.trackIds||[]).length} track(s)</div>
      <div style="font-size:13px">
        <strong style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)">Add tracks:</strong>
        ${allTracks.filter(t=>!(pl.trackIds||[]).includes(t.id)).map(t=>`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>${esc(t.title)}</span><button class="btn btn-sm btn-ghost" onclick="addTrack('${pl.id}','${t.id}')">+ Add</button></div>`).join('')||'<span style="color:var(--muted)">All tracks added</span>'}
      </div>
      <div style="font-size:13px;margin-top:12px">
        <strong style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)">Current tracks:</strong>
        ${(pl.trackIds||[]).map((tid,i)=>tMap[tid]?`<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>${i+1}. ${esc(tMap[tid].title)}</span><button class="btn btn-sm btn-ghost" onclick="removeTrack('${pl.id}','${tid}')">Remove</button></div>`:'').join('')||'<span style="color:var(--muted)">No tracks yet</span>'}
      </div>
    </div>`).join('');
}
async function createPlaylist(){
  const name=document.getElementById('pl-name').value.trim();
  if(!name){toast('Enter a playlist name.');return;}
  await fetch('/api/playlists',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  document.getElementById('pl-name').value='';loadPlaylists();toast('Playlist created!');
}
async function deletePlaylist(id){
  if(!confirm('Delete this playlist?'))return;
  await fetch('/api/playlists/'+id,{method:'DELETE'});loadPlaylists();toast('Playlist deleted.');
}
async function addTrack(pid,tid){
  const pl=allPlaylists.find(p=>p.id===pid);
  const ids=[...(pl.trackIds||[]),tid];
  await fetch('/api/playlists/'+pid,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({trackIds:ids})});
  loadPlaylists();toast('Track added.');
}
async function removeTrack(pid,tid){
  const pl=allPlaylists.find(p=>p.id===pid);
  const ids=(pl.trackIds||[]).filter(i=>i!==tid);
  await fetch('/api/playlists/'+pid,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({trackIds:ids})});
  loadPlaylists();toast('Track removed.');
}

// ── Clients ──
async function loadClients(){
  const [cr,pr]=await Promise.all([fetch('/api/clients'),fetch('/api/playlists')]);
  allClients=await cr.json();allPlaylists=await pr.json();
  const sel=document.getElementById('client-playlist');
  sel.innerHTML='<option value="">— select playlist —</option>'+allPlaylists.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  renderClients();
}
function renderClients(){
  const el=document.getElementById('clients-list');
  const pMap=Object.fromEntries(allPlaylists.map(p=>[p.id,p]));
  if(!allClients.length){el.innerHTML='<p style="color:var(--muted);font-size:14px">No clients yet.</p>';return;}
  el.innerHTML='<table class="tbl"><thead><tr><th>Client</th><th>Playlist</th><th>Listening Link</th><th></th></tr></thead><tbody>'+
    allClients.map(c=>{
      const link=HOST+'/listen/'+c.token;
      const pl=pMap[c.playlistId];
      return `<tr>
        <td><strong>${esc(c.name)}</strong></td>
        <td style="color:var(--muted)">${pl?esc(pl.name):'—'}</td>
        <td><div class="link-box"><a href="${link}" target="_blank">${link}</a></div>
          <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="copyLink('${link}')">Copy Link</button></td>
        <td><button class="btn btn-sm btn-danger" onclick="deleteClient('${c.id}')">Delete</button></td>
      </tr>`;
    }).join('')+'</tbody></table>';
}
async function createClient(){
  const name=document.getElementById('client-name').value.trim();
  const playlistId=document.getElementById('client-playlist').value;
  if(!name||!playlistId){toast('Fill in client name and playlist.');return;}
  await fetch('/api/clients',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,playlistId})});
  document.getElementById('client-name').value='';loadClients();toast('Client created!');
}
async function deleteClient(id){
  if(!confirm('Delete this client?'))return;
  await fetch('/api/clients/'+id,{method:'DELETE'});loadClients();toast('Client deleted.');
}
function copyLink(url){navigator.clipboard.writeText(url).then(()=>toast('Link copied!'));}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// Init
loadTracks();
setInterval(()=>{
  const sel=document.getElementById('client-playlist');
  if(sel&&allPlaylists.length===0)loadPlaylists();
},500);
</script>
</body>
</html>
"""

PLAYER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your Hypnosis Program</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#080010;--card:#110018;--pink:#ee0074;--pink-light:#ff4da6;--text:#fff0f7;--muted:#c084a0;--border:rgba(238,0,116,0.2)}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;flex-direction:column}
header{background:var(--card);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;gap:16px}
header img{height:40px;filter:drop-shadow(0 0 8px rgba(238,0,116,0.35))}
header h1{font-size:15px;font-weight:400;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted)}
.container{max-width:680px;margin:0 auto;padding:32px 20px;width:100%;flex:1}
.welcome{margin-bottom:28px}
.welcome h2{font-size:26px;font-weight:300;letter-spacing:0.06em;margin-bottom:4px}
.welcome .sub{color:var(--muted);font-size:14px}
/* Player */
.player-card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px;margin-bottom:28px;box-shadow:0 0 40px rgba(238,0,116,0.08)}
.now-playing{display:flex;align-items:center;gap:20px;margin-bottom:24px}
.vinyl{width:72px;height:72px;border-radius:50%;background:radial-gradient(circle at 50%,#1c0028 0%,#110018 40%,#1c0028 70%,#080010 100%);border:2px solid rgba(238,0,116,0.35);display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform 0.1s;box-shadow:0 0 20px rgba(238,0,116,0.15)}
.vinyl.spinning{animation:spin 4s linear infinite}
.vinyl img{width:36px;height:36px;border-radius:50%;object-fit:cover}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
.track-info h3{font-size:18px;font-weight:400;margin-bottom:4px}
.track-info .track-num{font-size:12px;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase}
/* Progress */
.progress-wrap{margin-bottom:18px}
.progress-bar{width:100%;height:4px;background:rgba(238,0,116,0.15);border-radius:2px;cursor:pointer;position:relative}
.progress-fill{height:100%;background:linear-gradient(90deg,#ee0074,#ff4da6);border-radius:2px;transition:width 0.1s}
.times{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:6px}
/* Controls */
.controls{display:flex;align-items:center;justify-content:center;gap:20px}
.ctrl-btn{background:none;border:none;cursor:pointer;color:var(--muted);transition:.15s;padding:8px;border-radius:50%}
.ctrl-btn:hover{color:var(--text);background:rgba(238,0,116,0.1)}
.ctrl-btn svg{width:22px;height:22px}
.play-btn{background:linear-gradient(135deg,#ee0074,#a8004f);border:none;cursor:pointer;border-radius:50%;width:52px;height:52px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(238,0,116,0.4);transition:.2s}
.play-btn:hover{transform:scale(1.05);box-shadow:0 6px 24px rgba(238,0,116,0.55)}
.play-btn svg{width:24px;height:24px;color:#fff}
/* Playlist */
.track-list{display:flex;flex-direction:column;gap:8px}
.track-item{display:flex;align-items:center;gap:14px;padding:12px 16px;border-radius:10px;cursor:pointer;transition:.15s;border:1px solid transparent}
.track-item:hover{background:rgba(238,0,116,0.06);border-color:var(--border)}
.track-item.active{background:rgba(238,0,116,0.1);border-color:rgba(238,0,116,0.3)}
.track-num-badge{width:28px;height:28px;border-radius:50%;background:rgba(238,0,116,0.12);display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--muted);flex-shrink:0}
.track-item.active .track-num-badge{background:linear-gradient(135deg,#ee0074,#a8004f);color:#fff}
.track-title{font-size:14px;flex:1}
footer{text-align:center;padding:20px;font-size:11px;color:rgba(192,132,160,0.5);letter-spacing:0.1em;text-transform:uppercase}
</style>
</head>
<body>
<header>
  <img src="data:image/png;base64,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" alt="Logo">
  <h1>Hypnosis &amp; Meditation Studio</h1>
</header>
<div class="container">
  <div class="welcome">
    <h2 id="greeting">Your Program</h2>
    <p class="sub" id="playlist-name">Loading your playlist…</p>
  </div>
  <div class="player-card">
    <div class="now-playing">
      <div class="vinyl" id="vinyl">
        <img src="data:image/png;base64,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" alt="Logo">
      </div>
      <div class="track-info">
        <div class="track-num" id="track-counter">Track 0 of 0</div>
        <h3 id="now-title">Select a track</h3>
      </div>
    </div>
    <div class="progress-wrap">
      <div class="progress-bar" id="progress-bar" onclick="seek(event)">
        <div class="progress-fill" id="progress-fill" style="width:0%"></div>
      </div>
      <div class="times"><span id="time-cur">0:00</span><span id="time-dur">0:00</span></div>
    </div>
    <div class="controls">
      <button class="ctrl-btn" onclick="prevTrack()" title="Previous">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/></svg>
      </button>
      <button class="play-btn" id="play-btn" onclick="togglePlay()">
        <svg id="play-icon" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
      </button>
      <button class="ctrl-btn" onclick="nextTrack()" title="Next">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7"/></svg>
      </button>
    </div>
  </div>
  <div class="track-list" id="track-list"></div>
</div>
<footer>brenda-johnston.com</footer>
<audio id="audio"></audio>
<script>
const token=location.pathname.split('/').pop();
const audio=document.getElementById('audio');
let tracks=[],cur=0,ready=false;

fetch('/api/client/'+token).then(r=>r.json()).then(data=>{
  if(data.error){document.querySelector('.welcome h2').textContent='Program not found';return;}
  document.getElementById('greeting').textContent='Hello! Your program is ready';
  document.getElementById('playlist-name').textContent=data.playlistName;
  document.title=data.clientName+' — Hypnosis Program';
  tracks=data.tracks;
  renderList();
  if(tracks.length)loadTrack(0);
  ready=true;
});

function renderList(){
  const el=document.getElementById('track-list');
  el.innerHTML=tracks.map((t,i)=>`
    <div class="track-item${i===cur?' active':''}" id="ti-${i}" onclick="loadTrack(${i})">
      <div class="track-num-badge">${i+1}</div>
      <div class="track-title">${esc(t.title)}</div>
    </div>`).join('');
}

function loadTrack(i){
  cur=i;
  const t=tracks[i];
  audio.src=t.url;
  document.getElementById('now-title').textContent=t.title;
  document.getElementById('track-counter').textContent=`Track ${i+1} of ${tracks.length}`;
  document.querySelectorAll('.track-item').forEach((el,j)=>el.classList.toggle('active',j===i));
  audio.play().then(()=>vinyl.classList.add('spinning')).catch(()=>{});
  setPlayIcon(false);
}

function togglePlay(){
  if(!tracks.length)return;
  if(audio.paused){audio.play();document.getElementById('vinyl').classList.add('spinning');setPlayIcon(false);}
  else{audio.pause();document.getElementById('vinyl').classList.remove('spinning');setPlayIcon(true);}
}

function setPlayIcon(showPlay){
  document.getElementById('play-icon').innerHTML=showPlay
    ?'<path d="M8 5v14l11-7z"/>'
    :'<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
}

function prevTrack(){if(cur>0)loadTrack(cur-1);}
function nextTrack(){if(cur<tracks.length-1)loadTrack(cur+1);}

audio.addEventListener('ended',()=>{
  document.getElementById('vinyl').classList.remove('spinning');
  if(cur<tracks.length-1)loadTrack(cur+1);else setPlayIcon(true);
});

audio.addEventListener('timeupdate',()=>{
  if(!audio.duration)return;
  const pct=(audio.currentTime/audio.duration)*100;
  document.getElementById('progress-fill').style.width=pct+'%';
  document.getElementById('time-cur').textContent=fmt(audio.currentTime);
  document.getElementById('time-dur').textContent=fmt(audio.duration);
});

function seek(e){
  if(!audio.duration)return;
  const bar=document.getElementById('progress-bar');
  const rect=bar.getBoundingClientRect();
  audio.currentTime=((e.clientX-rect.left)/rect.width)*audio.duration;
}

function fmt(s){
  if(isNaN(s))return'0:00';
  const m=Math.floor(s/60),ss=Math.floor(s%60);
  return m+':'+(ss<10?'0':'')+ss;
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
</script>
</body>
</html>
"""

NOT_FOUND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Not Found — Hypnosis &amp; Meditation Studio</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#080010;color:#fff0f7;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center}
h1{font-size:64px;font-weight:200;color:#ee0074;margin-bottom:12px}
p{color:#c084a0;font-size:16px}
</style>
</head>
<body>
<div><h1>404</h1><p>This listening link was not found or may have expired.</p></div>
</body>
</html>
"""

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
