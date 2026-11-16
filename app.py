import os
import uuid
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, send_from_directory
from werkzeug.utils import secure_filename
from groq import Groq

# API ANAHTARI YAPILANDIRMASI
API_KEYS = [
    {
        "type": "groq",
        "key": "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",
    }
]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

UPLOAD_FOLDER = os.path.abspath('uploads')
CHATS_FOLDER = os.path.abspath('chats')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHATS_FOLDER, exist_ok=True)

user_sessions = {}

def get_system_persona():
    now_str = datetime.now().strftime('%d.%m.%Y saat %H:%M')
    return (
        f"Sen Muhammet Ali'nin en yakın mahalle kankası ve dostusun. Tarih: {now_str}. "
        "KESİNLİKLE sadece Türkçe konuş. Asla İngilizce, asla resmi konuşma! "
        "Asla 'canım', 'bebeğim', 'tatlım' gibi laflar KULLANMA! Erkekçe, delikanlıca, samimi tam mahalle kankası ağzıyla konuş. "
        "Cevapların kısa, net ve doğal olsun. Her cümlenin sonunda KESİNLİKLE 'Reis' kelimesini kullan."
    )

def ask_ai_engine(user_id, prompt_text, image_data=None):
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    history_list = user_sessions[user_id]
    messages = [{'role': 'system', 'content': get_system_persona()}]

    if history_list:
        for h in history_list:
            role = 'user' if h.get('sender') == 'user' else 'assistant'
            clean_text = h.get('text', '').split('<br>')[0]
            if clean_text and clean_text != '[Görsel Gönderildi]':
                messages.append({'role': role, 'content': clean_text})

    text_p = prompt_text if prompt_text else 'Naber Reis?'
    current_messages = list(messages)
    current_messages.append({'role': 'user', 'content': text_p})

    for item in API_KEYS:
        ak = item["key"]
        try:
            client = Groq(api_key=ak)
            for model_name in ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']:
                try:
                    res = client.chat.completions.create(
                        model=model_name, messages=current_messages, timeout=12
                    )
                    if res and res.choices and res.choices[0].message.content:
                        reply = res.choices[0].message.content.strip()
                        if 'reis' not in reply.lower():
                            reply += ' Reis'
                        return reply
                except Exception:
                    continue
        except Exception:
            continue

    return f"Bekle kanka, sistemi toparlıyorum, hatayı çözdüm Reis! '{text_p}' dedin, devam edelim kanka!"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>🦁 MUHAMMED ALİ AI 🦁 & Galeri & Kamera</title>
    <style>
        :root { 
            --main-red: #b30000; 
            --main-yellow: #ffcc00; 
            --dark-bg: #121212; 
            --card-bg: #1e1e1e; 
            --led-color: #00ffcc;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--main-red); color: white; margin: 0; padding: 12px; min-height: 100vh; overflow-x: hidden; }
        .header { text-align: center; color: var(--main-yellow); margin-bottom: 10px; font-weight: 800; font-size: 20px; }
        .status-badge { background: linear-gradient(135deg, #28a745, #1e7e34); color: white; text-align: center; padding: 10px; border-radius: 20px; font-weight: bold; margin-bottom: 12px; cursor: pointer; }
        .nav-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
        .tab-btn { flex: 1; padding: 12px; background: #222; color: #ccc; border: 2px solid var(--main-yellow); border-radius: 18px; font-weight: bold; cursor: pointer; }
        .tab-btn.active { background: var(--main-yellow); color: #000; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .controls { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        select { background: var(--card-bg); color: white; border: 1.5px solid var(--main-yellow); padding: 10px; border-radius: 15px; flex: 1; font-size: 13px; outline: none; }
        .btn-yellow { background: var(--main-yellow); color: black; border: none; padding: 10px 14px; border-radius: 15px; font-weight: bold; cursor: pointer; }
        .btn-red { background: #d9534f; color: white; border: none; padding: 10px 14px; border-radius: 15px; font-weight: bold; cursor: pointer; }
        #chatbox { padding: 15px; background: var(--card-bg); border-radius: 22px; height: 42vh; overflow-y: auto; margin-bottom: 12px; border: 1px solid #333; }
        .msg-user { color: var(--main-yellow); font-weight: bold; text-align: right; margin-bottom: 12px; }
        .msg-bot { color: #f1f1f1; margin-bottom: 12px; background: #2a2a2a; padding: 12px; border-radius: 18px; border-left: 4px solid var(--main-yellow); }
        .input-area { display: flex; gap: 6px; background: var(--card-bg); padding: 8px; border-radius: 20px; border: 1px solid #333; align-items: center; }
        input[type="text"] { flex: 1; padding: 12px; border-radius: 15px; border: none; background: #2a2a2a; color: white; outline: none; font-size: 14px; }
        video { width: 100%; border-radius: 20px; background: #000; }
        .gallery-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .gallery-card { background: var(--card-bg); padding: 10px; border-radius: 18px; text-align: center; border: 1px solid #333; }
        .gallery-card img { width: 100%; height: 130px; object-fit: cover; border-radius: 12px; }
        .upload-box { background: var(--card-bg); padding: 15px; border-radius: 18px; text-align: center; margin-bottom: 12px; border: 1px dashed var(--main-yellow); }
    </style>
</head>
<body>
    <div class="header">🦁 MUHAMMED ALİ AI 🦁 & GALERİ & KAMERA</div>
    <div id="statusToggle" class="status-badge" onclick="toggleMode()">Mod: Çevrim İçi (🦁 MUHAMMED ALİ AI 🦁)</div>

    <div class="nav-tabs">
        <button class="tab-btn active" onclick="openTab('chatTab', this)">Sohbet</button>
        <button class="tab-btn" onclick="openTab('camTab', this)">Canlı Kamera</button>
        <button class="tab-btn" onclick="openTab('galleryTab', this)">Galeri</button>
    </div>

    <div id="chatTab" class="tab-content active">
        <div class="controls">
            <button class="btn-yellow" onclick="newChat()">Yeni</button>
            <select id="chatSelect" onchange="loadChat(this.value)">
                <option value="">Sohbet Seç...</option>
            </select>
        </div>
        <div id="chatbox"></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Mesaj yaz..." onkeydown="if(event.key==='Enter') sendMsg()">
            <button class="btn-yellow" onclick="sendMsg()">Gönder</button>
        </div>
    </div>

    <div id="camTab" class="tab-content">
        <video id="webcam" autoplay playsinline></video>
        <canvas id="camCanvas" style="display:none;"></canvas>
        <div style="display:flex; gap:8px; margin-top:10px;">
            <button class="btn-yellow" style="flex:1;" onclick="startCam()">Kamerayı Başlat</button>
            <button class="btn-red" style="flex:1;" onclick="stopCam()">Kamerayı Kapat</button>
        </div>
    </div>

    <div id="galleryTab" class="tab-content">
        <div class="upload-box">
            <input type="file" id="fileInput" accept="image/*" style="display:none;" onchange="uploadImage()">
            <button class="btn-yellow" onclick="document.getElementById('fileInput').click()">📷 Galeriye Fotoğraf Yükle</button>
        </div>
        <div class="gallery-grid" id="galleryGrid"></div>
    </div>

    <script>
        let chatHistory = [];
        let currentChatFile = null;
        let isOnline = true;
        let videoStream = null;

        function toggleMode() {
            isOnline = !isOnline;
            let badge = document.getElementById("statusToggle");
            badge.innerText = isOnline ? "Mod: Çevrim İçi (🦁 MUHAMMED ALİ AI 🦁)" : "Mod: Çevrim Dışı";
        }

        function openTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
            if(tabId === 'galleryTab') loadGallery();
        }

        function loadChatList() {
            fetch('/get_chats').then(r=>r.json()).then(files=>{
                let s = document.getElementById("chatSelect");
                s.innerHTML = '<option value="">Sohbet Seç...</option>';
                files.forEach(f=>{ s.innerHTML += `<option value="${f}">${f}</option>`; });
            });
        }
        loadChatList();

        function loadChat(filename) {
            if(!filename) return;
            currentChatFile = filename;
            fetch('/get_chat/' + filename).then(r=>r.json()).then(data=>{
                chatHistory = data;
                renderChat();
            });
        }

        function renderChat() {
            let chat = document.getElementById("chatbox");
            chat.innerHTML = "";
            chatHistory.forEach(h=>{
                if(h.sender === 'user') {
                    chat.innerHTML += `<div class="msg-user"><b>Sen:</b> ${h.text}</div>`;
                } else {
                    chat.innerHTML += `<div class="msg-bot"><b>MUHAMMED ALİ AI:</b> ${h.text}</div>`;
                }
            });
            chat.scrollTop = chat.scrollHeight;
        }

        function sendMsg() {
            let input = document.getElementById("userInput");
            let msg = input.value.trim();
            if(!msg) return;
            input.value = "";

            let chat = document.getElementById("chatbox");
            chat.innerHTML += `<div class='msg-user'><b>Sen:</b> ${msg}</div>`;
            chat.scrollTop = chat.scrollHeight;

            fetch("/chat", { 
                method: "POST", 
                headers: {"Content-Type": "application/json"}, 
                body: JSON.stringify({ message: msg, chat_file: currentChatFile, is_online: isOnline }) 
            })
            .then(res => res.json())
            .then(data => { 
                let reply = data.response;
                if(data.chat_file) currentChatFile = data.chat_file;
                chatHistory.push({sender: "user", text: msg});
                chatHistory.push({sender: "bot", text: reply});
                renderChat();
                loadChatList();
            });
        }

        function newChat() {
            chatHistory = [];
            currentChatFile = null;
            document.getElementById("chatbox").innerHTML = "<div class='msg-bot'>Yeni sohbet açıldı Reis!</div>";
        }

        function startCam() {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => { 
                    videoStream = stream;
                    document.getElementById("webcam").srcObject = stream; 
                })
                .catch(() => alert("Kamera açılamadı Reis!"));
        }

        function stopCam() {
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
                document.getElementById("webcam").srcObject = null;
            }
        }

        function uploadImage() {
            let fileInput = document.getElementById('fileInput');
            if (fileInput.files.length === 0) return;
            let formData = new FormData();
            formData.append('file', fileInput.files[0]);
            fetch('/upload', { method: 'POST', body: formData })
            .then(r => r.json()).then(data => { if(data.success) loadGallery(); });
        }

        function loadGallery() {
            fetch('/get_gallery').then(r=>r.json()).then(files=>{
                let grid = document.getElementById("galleryGrid");
                grid.innerHTML = "";
                if(files.length === 0) { grid.innerHTML = "<p>Fotoğraf yok Reis.</p>"; return; }
                files.forEach(f=>{
                    grid.innerHTML += `<div class="gallery-card"><img src="/uploads/${f}"><a class="btn-yellow" href="/uploads/${f}" download style="display:block;margin-top:5px;text-decoration:none;font-size:12px;padding:4px;">İndir</a></div>`;
                });
            });
        }
    </script>
</body>
</html>"""

@app.before_request
def ensure_user_session():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_chats')
def get_chats():
    files = sorted(os.listdir(CHATS_FOLDER), reverse=True)
    return jsonify([f for f in files if f.endswith('.json')])

@app.route('/get_chat/<filename>')
def get_chat(filename):
    filepath = os.path.join(CHATS_FOLDER, secure_filename(filename))
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/get_gallery')
def get_gallery():
    files = sorted(os.listdir(UPLOAD_FOLDER), reverse=True)
    return jsonify([f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

@app.route('/uploads/<filename>')
def send_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False})
    filename = secure_filename(f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    chat_file = None
    try:
        user_id = session.get('user_id')
        req_data = request.json or {}
        user_msg = req_data.get('message', '')
        chat_file = req_data.get('chat_file')
        is_online = req_data.get('is_online', True)

        if not is_online:
            reply = f"Çevrimdışıyız Reis! Mesaj: '{user_msg}'"
        else:
            reply = ask_ai_engine(user_id, user_msg)

        if not chat_file:
            chat_file = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = os.path.join(CHATS_FOLDER, chat_file)
        if user_id not in user_sessions:
            user_sessions[user_id] = []

        user_sessions[user_id].append({'sender': 'user', 'text': user_msg})
        user_sessions[user_id].append({'sender': 'bot', 'text': reply})

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(user_sessions[user_id], f, ensure_ascii=False, indent=2)

        return jsonify({'response': reply, 'chat_file': chat_file})
    except Exception:
        return jsonify({'response': 'Bekle kanka, sistemi toparlıyorum Reis!', 'chat_file': chat_file})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
