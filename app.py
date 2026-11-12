import base64
from datetime import datetime
import json
import os
from flask import (
    Flask,
    jsonify,
    render_template_string,
    request,
    send_from_directory,
)
from groq import Groq
import requests
from werkzeug.utils import secure_filename

GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

app = Flask(__name__)

UPLOAD_FOLDER = os.path.abspath('uploads')
CHATS_FOLDER = os.path.abspath('chats')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHATS_FOLDER, exist_ok=True)


def get_system_persona():
  now_str = datetime.now().strftime('%d.%m.%Y saat %H:%M')
  return (
      f"Sen Muhammet Ali'nin en yakın mahalle kankası ve dostusun. Tarih:"
      f" {now_str}. KESİNLİKLE sadece Türkçe konuş. Asla İngilizce, asla resmi"
      ' konuşma! Asla "canım", "bebeğim", "tatlım", "sevgilim", "hayatım" gibi'
      ' laflar KULLANMA! Erkekçe, delikanlıca, samimi tam mahalle kankası ağzıyla'
      " konuş. Kullanıcı fotoğraf gönderdiyse fotoğrafı çok dikkatli incele ve"
      " ne olduğunu kanka tarzında anlat. Sadece kullanıcının söylediğini"
      " tekrarlama! Cevapların kısa, net ve doğal olsun. Her cümlenin sonunda"
      " KESİNLİKLE 'Reis' kelimesini kullan."
  )


def ask_ai_engine(
    prompt_text, history_list, image_data=None, target_model=None
):
  messages = [{'role': 'system', 'content': get_system_persona()}]

  if history_list:
    for h in history_list:
      role = 'user' if h.get('sender') == 'user' else 'assistant'
      clean_text = h.get('text', '').split('<br>')[0]
      if clean_text and clean_text != '[Görsel Gönderildi]':
        messages.append({'role': role, 'content': clean_text})

  # GÖRSEL ANALİZ İÇİN VİZYON MOTORLARI
  if image_data:
    vision_messages = list(messages)
    vision_messages.append({
        'role': 'user',
        'content': [
            {
                'type': 'text',
                'text': (
                    prompt_text
                    if prompt_text
                    else 'Bu fotoğrafta tam olarak ne var Reis? Detaylı anlat.'
                ),
            },
            {'type': 'image_url', 'image_url': {'url': image_data}},
        ],
    })

    v_models = [
        'llama-3.2-11b-vision-instruct',
        'llama-3.2-90b-vision-instruct',
    ]
    for vm in v_models:
      try:
        res = groq_client.chat.completions.create(
            model=vm, messages=vision_messages, timeout=15
        )
        if res and res.choices and res.choices[0].message.content:
          reply = res.choices[0].message.content.strip()
          if 'reis' not in reply.lower():
            reply += ' Reis'
          return reply
      except Exception as e_vis:
        print(f'Vizyon Motor Hatası ({vm}):', e_vis)

  # METİN İÇİN GROQ MOTORLARI
  engine_pool = [
      'llama-3.3-70b-versatile',
      'llama-3.1-8b-instant',
      'meta-llama/llama-4-scout-17b-16e-instruct',
      'openai/gpt-oss-120b',
      'openai/gpt-oss-20b',
  ]

  text_p = prompt_text if prompt_text else 'Naber Reis?'
  messages.append({'role': 'user', 'content': text_p})

  for model_name in engine_pool:
    try:
      res = groq_client.chat.completions.create(
          model=model_name, messages=messages, timeout=12
      )
      if res and res.choices and res.choices[0].message.content:
        reply = res.choices[0].message.content.strip()
        if 'reis' not in reply.lower():
          reply += ' Reis'
        return reply
    except Exception as e:
      print(f'Motor Hatası ({model_name}):', e)
      continue

  return (
      f"Aynen öyle Reis, '{text_p}' dedin. Anlat bakalım detayını kanka!"
  )


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
            --led-thinking: #d633ff;
            --led-speaking: #ffcc00;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--main-red); color: white; margin: 0; padding: 12px; position: relative; min-height: 100vh; overflow-x: hidden; touch-action: manipulation; }
        
        .header { text-align: center; color: var(--main-yellow); margin-bottom: 10px; font-weight: 800; font-size: 20px; text-shadow: 1px 1px 3px rgba(0,0,0,0.6); }
        
        .status-badge { 
            background: linear-gradient(135deg, #28a745, #1e7e34); 
            color: white; text-align: center; padding: 10px; border-radius: 20px; 
            font-weight: bold; margin-bottom: 12px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: all 0.3s;
        }
        .status-badge.offline { background: linear-gradient(135deg, #6c757d, #495057); }
        
        .nav-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
        .tab-btn { flex: 1; padding: 12px; background: #222; color: #ccc; border: 2px solid var(--main-yellow); border-radius: 18px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .tab-btn.active { background: var(--main-yellow); color: #000; box-shadow: 0 0 12px rgba(255, 204, 0, 0.5); }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .controls { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        select { background: var(--card-bg); color: white; border: 1.5px solid var(--main-yellow); padding: 10px; border-radius: 15px; flex: 1; font-size: 13px; outline: none; }
        .btn-yellow { background: var(--main-yellow); color: black; border: none; padding: 10px 14px; border-radius: 15px; font-weight: bold; cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }
        .btn-red { background: #d9534f; color: white; border: none; padding: 10px 14px; border-radius: 15px; font-weight: bold; cursor: pointer; }

        .version-info-box {
            background: #111;
            color: var(--main-yellow);
            border: 1px solid var(--main-yellow);
            padding: 8px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        }

        #chatbox { padding: 15px; background: var(--card-bg); border-radius: 22px; height: 42vh; overflow-y: auto; margin-bottom: 12px; border: 1px solid #333; box-shadow: inset 0 2px 8px rgba(0,0,0,0.5); }
        .msg-user { color: var(--main-yellow); font-weight: bold; text-align: right; margin-bottom: 12px; }
        .msg-bot { color: #f1f1f1; margin-bottom: 12px; background: #2a2a2a; padding: 12px; border-radius: 18px; border-left: 4px solid var(--main-yellow); position: relative; }
        
        .audio-controls { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
        .btn-audio { background: #333; color: var(--main-yellow); border: 1px solid var(--main-yellow); padding: 4px 10px; border-radius: 10px; font-size: 11px; cursor: pointer; }

        .timer-badge { font-size: 11px; color: var(--main-yellow); margin-top: 6px; display: block; opacity: 0.9; }
        
        .input-area { display: flex; gap: 6px; background: var(--card-bg); padding: 8px; border-radius: 20px; border: 1px solid #333; align-items: center; }
        input[type="text"] { flex: 1; padding: 12px; border-radius: 15px; border: none; background: #2a2a2a; color: white; outline: none; font-size: 14px; }
        
        video, canvas { width: 100%; border-radius: 20px; background: #000; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        
        .gallery-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .gallery-card { background: var(--card-bg); padding: 10px; border-radius: 18px; text-align: center; border: 1px solid #333; }
        .gallery-card img { width: 100%; height: 130px; object-fit: cover; border-radius: 12px; }
        .btn-dl { background: #28a745; color: white; text-decoration: none; display: inline-block; padding: 6px 12px; margin-top: 8px; border-radius: 10px; font-size: 12px; font-weight: bold; }
        
        .upload-box { background: var(--card-bg); padding: 15px; border-radius: 18px; text-align: center; margin-bottom: 12px; border: 1px dashed var(--main-yellow); }
        
        .cam-prompt-label { text-align: center; font-weight: bold; color: var(--main-yellow); margin-top: 10px; margin-bottom: 6px; font-size: 14px; }

        #chatImagePreviewArea {
            display: none;
            background: #2a2a2a;
            border: 1.5px dashed var(--main-yellow);
            border-radius: 15px;
            padding: 10px;
            margin-bottom: 8px;
            text-align: center;
        }
        #chatImgPreview {
            max-height: 120px;
            max-width: 90%;
            border-radius: 10px;
            margin-top: 6px;
            border: 1px solid var(--main-yellow);
            object-fit: contain;
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        #introOverlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: #000000;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 15px;
            box-sizing: border-box;
            overflow: hidden;
        }

        #introRobotWrapper {
            position: relative;
            transform: translateY(-150px);
            transition: transform 1.5s cubic-bezier(0.25, 1, 0.5, 1);
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        #introRobotWrapper.arrived {
            transform: translateY(0px);
        }

        #miniRobotContainer {
            position: fixed;
            bottom: 30px;
            left: 20px;
            z-index: 999;
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: grab;
            user-select: none;
            touch-action: none;
            transition: left 0.1s linear, top 0.1s linear;
        }

        .robot-full-body {
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            padding: 5px;
        }

        .led-robot-head {
            width: 58px;
            height: 48px;
            background: #111;
            border: 2.5px solid var(--current-led, var(--led-color));
            border-radius: 12px;
            box-shadow: 0 0 15px var(--current-led, var(--led-color));
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: relative;
            z-index: 2;
            transition: all 0.4s ease;
        }

        .led-eyes { display: flex; gap: 12px; margin-bottom: 4px; }
        .led-eye { width: 8px; height: 8px; background: var(--current-led, var(--led-color)); border-radius: 2px; box-shadow: 0 0 6px var(--current-led, var(--led-color)); transition: all 0.4s ease; }
        .led-mouth { width: 20px; height: 3px; background: var(--current-led, var(--led-color)); border-radius: 2px; box-shadow: 0 0 6px var(--current-led, var(--led-color)); transition: all 0.4s ease; }

        .robot-torso {
            width: 42px;
            height: 38px;
            background: #222;
            border: 2px solid var(--current-led, var(--led-color));
            border-radius: 8px;
            margin-top: 2px;
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.4s ease;
            overflow: hidden;
        }
        
        #robotHeldPhoto {
            display: none;
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 6px;
            overflow: hidden;
            z-index: 5;
            animation: pulsePhoto 0.8s infinite alternate;
        }
        #robotHeldPhoto img { width: 100%; height: 100%; object-fit: cover; }
        @keyframes pulsePhoto { 0% { transform: scale(0.95); opacity: 0.8; } 100% { transform: scale(1.05); opacity: 1; } }

        .robot-heart {
            width: 10px;
            height: 10px;
            background: var(--current-led, var(--led-color));
            border-radius: 50%;
            box-shadow: 0 0 8px var(--current-led, var(--led-color));
            animation: pulseHeart 1s infinite alternate;
            transition: all 0.4s ease;
            z-index: 6;
        }
        @keyframes pulseHeart { 0% { transform: scale(0.8); opacity: 0.6; } 100% { transform: scale(1.2); opacity: 1; } }

        .robot-arm {
            width: 7px;
            height: 26px;
            background: var(--current-led, var(--led-color));
            border-radius: 4px;
            position: absolute;
            top: 52px;
            box-shadow: 0 0 6px var(--current-led, var(--led-color));
            transition: background 0.4s ease, box-shadow 0.4s ease, transform 0.3s ease;
            transform-origin: top center;
        }
        .robot-arm.left { left: -10px; transform: rotate(15deg); }
        .robot-arm.right { right: -10px; transform: rotate(-15deg); }

        .idle-anim .robot-arm.left { animation: idleArmLeft 1.2s infinite alternate ease-in-out; }
        .idle-anim .robot-arm.right { animation: idleArmRight 1.2s infinite alternate ease-in-out; }
        .idle-anim .robot-leg.left { animation: idleLegLeft 1.2s infinite alternate ease-in-out; }
        .idle-anim .robot-leg.right { animation: idleLegRight 1.2s infinite alternate ease-in-out; }

        @keyframes idleArmLeft { 0% { transform: rotate(10deg); } 100% { transform: rotate(35deg); } }
        @keyframes idleArmRight { 0% { transform: rotate(-10deg); } 100% { transform: rotate(-35deg); } }
        @keyframes idleLegLeft { 0% { transform: rotate(-10deg); } 100% { transform: rotate(10deg); } }
        @keyframes idleLegRight { 0% { transform: rotate(10deg); } 100% { transform: rotate(-10deg); } }

        .walking .robot-leg.left { animation: walkLegLeft 0.35s infinite alternate ease-in-out; }
        .walking .robot-leg.right { animation: walkLegRight 0.35s infinite alternate ease-in-out; }
        .walking .robot-arm.left { animation: walkArmLeft 0.35s infinite alternate ease-in-out; }
        .walking .robot-arm.right { animation: walkArmRight 0.35s infinite alternate ease-in-out; }

        @keyframes walkLegLeft { 0% { transform: rotate(-30deg); } 100% { transform: rotate(30deg); } }
        @keyframes walkLegRight { 0% { transform: rotate(30deg); } 100% { transform: rotate(-30deg); } }
        @keyframes walkArmLeft { 0% { transform: rotate(30deg); } 100% { transform: rotate(-30deg); } }
        @keyframes walkArmRight { 0% { transform: rotate(-30deg); } 100% { transform: rotate(30deg); } }

        .talking .robot-arm.left { animation: waveLeft 0.5s infinite alternate ease-in-out; }
        .talking .robot-arm.right { animation: waveRight 0.5s infinite alternate ease-in-out; }
        @keyframes waveLeft { 0% { transform: rotate(15deg); } 100% { transform: rotate(-30deg); } }
        @keyframes waveRight { 0% { transform: rotate(-15deg); } 100% { transform: rotate(30deg); } }

        .thinking .led-robot-head { transform: translateY(3px) rotate(8deg); }

        .pressing .robot-arm.right {
            transform: rotate(-115deg) scaleY(1.3) !important;
            animation: none !important;
        }

        .robot-legs { display: flex; gap: 12px; margin-top: 1px; }
        .robot-leg { width: 7px; height: 24px; background: var(--current-led, var(--led-color)); border-radius: 4px; box-shadow: 0 0 6px var(--current-led, var(--led-color)); transition: all 0.4s ease; transform-origin: top center; }

        .robot-speech-bubble {
            background: rgba(18, 18, 18, 0.95);
            color: var(--current-led, var(--led-color));
            border: 1.5px solid var(--current-led, var(--led-color));
            padding: 12px 18px;
            border-radius: 18px;
            font-size: 14px;
            margin-bottom: 15px;
            width: auto;
            max-width: 85vw;
            min-height: 24px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.8);
            font-weight: 700;
            white-space: normal;
            word-wrap: break-word;
            line-height: 1.4;
            transition: all 0.4s ease;
        }

        .robot-actions { display: flex; gap: 4px; margin-top: 8px; flex-wrap: wrap; justify-content: center; }
        .btn-robot-action { background: var(--led-color); color: #000; border: none; padding: 6px 10px; border-radius: 10px; font-size: 11px; font-weight: bold; cursor: pointer; }
        .btn-robot-close { background: #d9534f; color: #fff; border: none; padding: 6px 10px; border-radius: 10px; font-size: 11px; font-weight: bold; cursor: pointer; }

        .intro-row {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-top: 15px;
        }

        #introStartBtn {
            opacity: 0;
            transform: scale(0.5);
            transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            background: var(--main-yellow);
            color: black;
            border: none;
            padding: 12px 22px;
            border-radius: 20px;
            font-weight: 900;
            font-size: 14px;
            box-shadow: 0 0 20px var(--main-yellow);
            cursor: pointer;
        }

        #introStartBtn.visible {
            opacity: 1;
            transform: scale(1);
        }

        #introStartBtn.pressed {
            transform: scale(0.9) !important;
            background: #28a745 !important;
            box-shadow: 0 0 30px #28a745 !important;
            color: white !important;
        }

        #robotModal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }
        .robot-modal-content {
            background: #1e1e1e;
            border: 2px solid var(--current-led, var(--led-color));
            border-radius: 20px;
            padding: 16px;
            width: 85%;
            max-width: 320px;
            text-align: center;
            box-shadow: 0 0 20px rgba(0,255,204,0.4);
        }
    </style>
</head>
<body>

    <div id="introOverlay">
        <div class="robot-speech-bubble" id="introBubble" style="opacity: 0;">Selam Reis! Bekle yapay zekayı çalıştırıyorum...</div>
        
        <div id="introRobotWrapper">
            <div class="intro-row">
                <div class="robot-full-body walking" id="introRobotBody" style="transform: scale(1.3);">
                    <div class="led-robot-head">
                        <div class="led-eyes">
                            <div class="led-eye"></div>
                            <div class="led-eye"></div>
                        </div>
                        <div class="led-mouth"></div>
                    </div>
                    
                    <div class="robot-arm left"></div>
                    <div class="robot-torso">
                        <div class="robot-heart"></div>
                    </div>
                    <div class="robot-arm right"></div>
                    
                    <div class="robot-legs">
                        <div class="robot-leg left"></div>
                        <div class="robot-leg right"></div>
                    </div>
                </div>

                <button id="introStartBtn" onclick="triggerManualLaunch()">🚀 Yapay Zekayı Başlat</button>
            </div>
        </div>
    </div>

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
            <button class="btn-yellow" id="robotToggleBtn" onclick="toggleMiniRobot()" style="background:#00ffcc; color:#000;">🤖 LED Robot Aktif</button>

            <select id="groqModelSelect" onchange="updateVersionDisplay()">
                <option value="llama-3.3-70b-versatile">🚀 Ultra Güçlü Groq Motor Havuzu</option>
            </select>

            <select id="chatSelect" onchange="loadChat(this.value)">
                <option value="">Sohbet Seç...</option>
            </select>
        </div>

        <div class="version-info-box" id="activeVersionDisplay">
            Aktif Sürüm: 🚀 Ultra Güçlü Groq Motor Havuzu
        </div>

        <div id="chatbox"></div>

        <div id="chatImagePreviewArea">
            <div style="font-size: 13px; font-weight: bold; color: var(--main-yellow);">
                Fotoğraf hakkında bir şey bahsetmek ister misiniz?
            </div>
            <img id="chatImgPreview" src="" alt="Önizleme">
            <div style="margin-top: 6px; display: flex; gap: 6px; justify-content: center;">
                <button class="btn-yellow" style="background:#28a745; color:white; font-size: 12px; padding: 6px 10px;" onclick="sendMsg(true)">⚡ Direkt Gönder</button>
                <button class="btn-red" style="font-size: 12px; padding: 6px 10px;" onclick="clearChatImage()">❌ Kaldır</button>
            </div>
        </div>

        <div class="input-area">
            <input type="file" id="chatFileInput" accept="image/*" style="display:none;" onchange="handleChatImageSelect(event)">
            <button class="btn-yellow" onclick="document.getElementById('chatFileInput').click()" title="Fotoğraf Yükle">📷 Galeri</button>

            <input type="text" id="userInput" placeholder="Mesaj yaz..." onkeydown="if(event.key==='Enter') sendMsg(false)">
            <button class="btn-yellow" onclick="startVoice('userInput')">🎙️</button>
            <button class="btn-yellow" onclick="sendMsg(false)">Gönder</button>
        </div>
    </div>

    <div id="camTab" class="tab-content">
        <video id="webcam" autoplay playsinline></video>
        <canvas id="camCanvas" style="display:none;"></canvas>
        <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
            <button class="btn-yellow" style="flex:1;" onclick="startCam()">Kamerayı Başlat</button>
            <button class="btn-yellow" style="flex:1;" onclick="switchCam()">Kamera Çevir</button>
            <button class="btn-red" style="flex:1;" onclick="stopCam()">Kamerayı Kapat</button>
        </div>

        <div class="cam-prompt-label">Fotoğraf hakkında bir şey sormak istiyor musunuz?</div>

        <div class="input-area" style="flex-wrap:wrap;">
            <input type="text" id="camInput" placeholder="Soru yazın..." onkeydown="if(event.key==='Enter') sendCamMsg(false)">
            <button class="btn-yellow" onclick="startVoiceAndSendCam()" title="Sesli Soru Sor ve Gönder">🎙️ Sesli Soru Sor</button>
            <button class="btn-yellow" onclick="sendCamMsg(false)">Gönder</button>
            <button class="btn-yellow" style="background:#28a745; color:white;" onclick="sendCamMsg(true)" title="Metinsiz Direkt Görsel Gönder">⚡ Direkt Gönder</button>
        </div>

        <div id="camChatBox" style="margin-top:12px; background:var(--card-bg); padding:12px; border-radius:18px; border:1px solid #333;">
            <div id="camStatus">Asistan Yanıtı: Kamera bekleniyor Reis.</div>
            <div class="audio-controls" id="camAudioControls" style="display:none;">
                <button class="btn-audio" onclick="speakTextById('camStatus')">🔊 Oku</button>
                <button class="btn-audio" onclick="stopSpeech()">⏹️ Durdur</button>
                <button class="btn-audio" onclick="copyTextById('camStatus')">📋 Kopyala</button>
            </div>
        </div>
    </div>

    <div id="galleryTab" class="tab-content">
        <div class="upload-box">
            <input type="file" id="fileInput" accept="image/*" style="display:none;" onchange="uploadImage()">
            <button class="btn-yellow" onclick="document.getElementById('fileInput').click()">📷 Galeriye Fotoğraf Yükle</button>
        </div>
        <div class="gallery-grid" id="galleryGrid"></div>
    </div>

    <div id="miniRobotContainer" style="display:none;" class="idle-anim">
        <div class="robot-speech-bubble" id="robotBubble">Selam Reis! Buradayım, ne yapıyoruz? 🤖</div>
        
        <div class="robot-full-body" id="robotFullBody" onclick="openRobotModal()">
            <div class="led-robot-head" id="robotHead">
                <div class="led-eyes">
                    <div class="led-eye"></div>
                    <div class="led-eye"></div>
                </div>
                <div class="led-mouth" id="robotMouth"></div>
            </div>
            
            <div class="robot-arm left"></div>
            <div class="robot-torso">
                <div id="robotHeldPhoto">
                    <img id="robotHeldImg" src="" alt="Fotoğraf">
                </div>
                <div class="robot-heart"></div>
            </div>
            <div class="robot-arm right"></div>
            
            <div class="robot-legs">
                <div class="robot-leg left"></div>
                <div class="robot-leg right"></div>
            </div>
        </div>

        <div class="robot-actions">
            <button class="btn-robot-action" onclick="openRobotModal()">🤖 Robota Soru / Fotoğraf Gönder</button>
            <button class="btn-robot-close" onclick="toggleMiniRobot()">❌ Kapat</button>
        </div>
    </div>

    <div id="robotModal">
        <div class="robot-modal-content">
            <h3 style="color:var(--current-led, var(--led-color)); margin-top:0;">🤖 Robota Mesaj Gönder</h3>
            
            <div id="robotModalImgPreview" style="display:none; margin-bottom:10px;">
                <img id="robotModalImg" src="" style="max-height:100px; border-radius:10px; border:1px solid var(--led-color);">
            </div>

            <input type="text" id="robotModalInput" placeholder="Mesajını yaz Reis..." style="width:90%; padding:10px; border-radius:12px; border:none; background:#333; color:white; margin-bottom:10px; font-size:13px;">

            <div style="display:flex; gap:6px; justify-content:center; flex-wrap:wrap; margin-bottom:12px;">
                <input type="file" id="robotFileInput" accept="image/*" style="display:none;" onchange="handleRobotModalImage(event)">
                <button class="btn-robot-action" style="background:#ffcc00; color:black;" onclick="document.getElementById('robotFileInput').click()">📷 Fotoğraf Seç</button>
                <button class="btn-robot-action" style="background:#00ffcc; color:black;" onclick="startVoice('robotModalInput')">🎙️ Mikrofon ile Söyle</button>
            </div>

            <div style="display:flex; gap:8px; justify-content:center;">
                <button class="btn-robot-action" style="background:#28a745; color:white; padding:8px 16px;" onclick="sendRobotModalMsg()">🚀 Gönder</button>
                <button class="btn-robot-close" style="padding:8px 16px;" onclick="closeRobotModal()">❌ İptal</button>
            </div>
        </div>
    </div>

    <script>
        let chatHistory = [];
        let currentChatFile = null;
        let facingMode = "user";
        let videoStream = null;
        let isOnline = true;
        let isRobotActive = true;
        let typingInterval = null;
        let selectedChatBase64Image = null;
        let selectedRobotBase64Image = null;

        let robotPosX = 20;
        let robotPosY = window.innerHeight - 200;
        let walkDirection = 1;
        let walkTimer = null;

        window.addEventListener("load", () => {
            playIntroSequence();
        });

        function setRobotMood(mood) {
            let color = "#00ffcc";
            if(mood === "thinking") color = "#d633ff";
            if(mood === "speaking") color = "#ffcc00";
            document.documentElement.style.setProperty('--current-led', color);
        }

        function playIntroSequence() {
            let robotWrapper = document.getElementById("introRobotWrapper");
            let robotBody = document.getElementById("introRobotBody");
            let bubble = document.getElementById("introBubble");
            let btn = document.getElementById("introStartBtn");

            setRobotMood("speaking");

            setTimeout(() => {
                robotWrapper.classList.add("arrived");
            }, 200);

            setTimeout(() => {
                robotBody.classList.remove("walking");
                robotBody.classList.add("idle-anim");
                bubble.style.opacity = "1";

                let introText = "Selam Reis! Bekle yapay zekayı çalıştırıyorum...";
                bubble.innerText = "";
                let i = 0;

                let typing = setInterval(() => {
                    if (i < introText.length) {
                        bubble.innerText += introText.charAt(i);
                        i++;
                    } else {
                        clearInterval(typing);
                        btn.classList.add("visible");

                        setTimeout(() => {
                            robotBody.classList.add("pressing");
                            setTimeout(() => {
                                btn.classList.add("pressed");
                                setTimeout(() => {
                                    launchMainApp();
                                }, 700);
                            }, 400);
                        }, 500);
                    }
                }, 40);

                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utter = new SpeechSynthesisUtterance(introText);
                    utter.lang = 'tr-TR';
                    utter.rate = 0.85;
                    window.speechSynthesis.speak(utter);
                }
            }, 1800);
        }

        function triggerManualLaunch() {
            let robotBody = document.getElementById("introRobotBody");
            let btn = document.getElementById("introStartBtn");
            robotBody.classList.add("pressing");
            btn.classList.add("pressed");
            setTimeout(() => {
                launchMainApp();
            }, 600);
        }

        function launchMainApp() {
            let overlay = document.getElementById("introOverlay");
            if (overlay.style.display === "none") return;
            
            overlay.style.display = "none";
            setRobotMood("normal");
            
            let robotElem = document.getElementById("miniRobotContainer");
            robotElem.style.display = "flex";
            robotPosY = window.innerHeight - 220;
            robotPosX = 20;
            robotElem.style.left = robotPosX + "px";
            robotElem.style.top = robotPosY + "px";
            
            startRobotRoaming();
            speakSlowlyAndType("Yapay zeka aktif Reis, ne yapıyoruz?");
        }

        function startRobotRoaming() {
            let robotElem = document.getElementById("miniRobotContainer");
            if (walkTimer) clearInterval(walkTimer);
            walkTimer = setInterval(() => {
                if (isDragging || !isRobotActive) return;

                if (Math.random() < 0.05) {
                    walkDirection *= -1;
                }

                let maxX = window.innerWidth - robotElem.offsetWidth - 20;
                let minX = 20;

                robotPosX += walkDirection * 3;

                if (robotPosX >= maxX) {
                    robotPosX = maxX;
                    walkDirection = -1;
                } else if (robotPosX <= minX) {
                    robotPosX = minX;
                    walkDirection = 1;
                }

                robotElem.style.left = robotPosX + "px";
                robotElem.style.top = robotPosY + "px";
                robotElem.style.bottom = "auto";
                robotElem.style.right = "auto";

                robotElem.classList.remove("idle-anim");
                robotElem.classList.add("walking");
            }, 100);
        }

        function updateVersionDisplay() {
            let selectElem = document.getElementById("groqModelSelect");
            let selectedText = selectElem.options[selectElem.selectedIndex].text;
            document.getElementById("activeVersionDisplay").innerText = "Aktif Sürüm: " + selectedText;
        }

        function handleChatImageSelect(event) {
            let file = event.target.files[0];
            if (!file) return;

            let reader = new FileReader();
            reader.onload = function(e) {
                selectedChatBase64Image = e.target.result;
                let imgElem = document.getElementById("chatImgPreview");
                imgElem.src = selectedChatBase64Image;
                document.getElementById("chatImagePreviewArea").style.display = "block";
            };
            reader.readAsDataURL(file);
        }

        function clearChatImage() {
            selectedChatBase64Image = null;
            document.getElementById("chatFileInput").value = "";
            document.getElementById("chatImagePreviewArea").style.display = "none";
        }

        const robotElem = document.getElementById("miniRobotContainer");
        let isDragging = false;
        let initialX = 0, initialY = 0;

        robotElem.addEventListener("mousedown", dragStart);
        robotElem.addEventListener("touchstart", dragStart, {passive: false});

        function dragStart(e) {
            if(e.target.tagName === "BUTTON") return;
            isDragging = true;
            robotElem.classList.remove("walking");
            robotElem.classList.add("idle-anim");
            robotElem.style.cursor = "grabbing";
            
            let clientX = e.type === "touchstart" ? e.touches[0].clientX : e.clientX;
            let clientY = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;
            
            initialX = clientX - robotElem.offsetLeft;
            initialY = clientY - robotElem.offsetTop;

            document.addEventListener("mousemove", drag);
            document.addEventListener("touchmove", drag, {passive: false});
            document.addEventListener("mouseup", dragEnd);
            document.addEventListener("touchend", dragEnd);
        }

        function drag(e) {
            if (!isDragging) return;
            if(e.cancelable) e.preventDefault();
            
            let clientX = e.type === "touchmove" ? e.touches[0].clientX : e.clientX;
            let clientY = e.type === "touchmove" ? e.touches[0].clientY : e.clientY;

            let currentX = clientX - initialX;
            let currentY = clientY - initialY;

            let maxX = window.innerWidth - robotElem.offsetWidth;
            let maxY = window.innerHeight - robotElem.offsetHeight;

            currentX = Math.max(0, Math.min(currentX, maxX));
            currentY = Math.max(0, Math.min(currentY, maxY));

            robotPosX = currentX;
            robotPosY = currentY;

            robotElem.style.left = currentX + "px";
            robotElem.style.top = currentY + "px";
            robotElem.style.bottom = "auto";
            robotElem.style.right = "auto";
        }

        function dragEnd() {
            isDragging = false;
            robotElem.style.cursor = "grab";
            document.removeEventListener("mousemove", drag);
            document.removeEventListener("touchmove", drag);
            startRobotRoaming();
        }

        function toggleMode() {
            isOnline = !isOnline;
            let badge = document.getElementById("statusToggle");
            if(isOnline) {
                badge.innerText = "Mod: Çevrim İçi (🦁 MUHAMMED ALİ AI 🦁)";
                badge.classList.remove("offline");
            } else {
                badge.innerText = "Mod: Çevrim Dışı (Çevrim Dışı Asistan)";
                badge.classList.add("offline");
            }
        }

        function setRobotThinking(thinking, imageUrl = null) {
            let robot = document.getElementById("miniRobotContainer");
            let heldPhoto = document.getElementById("robotHeldPhoto");
            let heldImg = document.getElementById("robotHeldImg");

            if(thinking) {
                setRobotMood("thinking");
                robot.classList.add("thinking");
                if(imageUrl) {
                    heldImg.src = imageUrl;
                    heldPhoto.style.display = "block";
                }
            } else {
                setRobotMood("normal");
                robot.classList.remove("thinking");
                heldPhoto.style.display = "none";
            }
        }

        function speakSlowlyAndType(text) {
            let cleanText = text.replace(/<[^>]*>?/gm, '');
            let elem = document.getElementById("robotBubble");
            let body = document.getElementById("miniRobotContainer");

            if(typingInterval) clearInterval(typingInterval);
            stopSpeech();

            setRobotMood("speaking");
            elem.innerText = "";
            let i = 0;
            
            typingInterval = setInterval(() => {
                if (i < cleanText.length) {
                    elem.innerText += cleanText.charAt(i);
                    i++;
                } else {
                    clearInterval(typingInterval);
                }
            }, 45);

            if ('speechSynthesis' in window) {
                let utter = new SpeechSynthesisUtterance(cleanText);
                utter.lang = 'tr-TR';
                utter.rate = 0.85;

                utter.onstart = () => { if(body) body.classList.add("talking"); };
                utter.onend = () => { 
                    if(body) body.classList.remove("talking"); 
                    setRobotMood("normal");
                };
                utter.onerror = () => { 
                    if(body) body.classList.remove("talking"); 
                    setRobotMood("normal");
                };

                window.speechSynthesis.speak(utter);
            } else {
                setTimeout(() => { setRobotMood("normal"); }, 2000);
            }
        }

        function toggleMiniRobot() {
            isRobotActive = !isRobotActive;
            let robot = document.getElementById("miniRobotContainer");
            let btn = document.getElementById("robotToggleBtn");

            if(isRobotActive) {
                robot.style.display = "flex";
                btn.innerText = "🤖 LED Robot Aktif";
                speakSlowlyAndType("Selam Reis! Buradayım, ne yapıyoruz?");
                startRobotRoaming();
            } else {
                robot.style.display = "none";
                btn.innerText = "🤖 Sürüklenebilir LED Robot";
                if(typingInterval) clearInterval(typingInterval);
                if(walkTimer) clearInterval(walkTimer);
                stopSpeech();
            }
        }

        function openRobotModal() {
            document.getElementById("robotModal").style.display = "flex";
        }

        function closeRobotModal() {
            document.getElementById("robotModal").style.display = "none";
            selectedRobotBase64Image = null;
            document.getElementById("robotModalImgPreview").style.display = "none";
            document.getElementById("robotFileInput").value = "";
            document.getElementById("robotModalInput").value = "";
        }

        function handleRobotModalImage(event) {
            let file = event.target.files[0];
            if(!file) return;
            let reader = new FileReader();
            reader.onload = function(e) {
                selectedRobotBase64Image = e.target.result;
                document.getElementById("robotModalImg").src = selectedRobotBase64Image;
                document.getElementById("robotModalImgPreview").style.display = "block";
            };
            reader.readAsDataURL(file);
        }

        function sendRobotModalMsg() {
            let promptText = document.getElementById("robotModalInput").value.trim();
            let sentImage = selectedRobotBase64Image;
            
            if(!promptText && !sentImage) return;

            closeRobotModal();
            document.getElementById("robotBubble").innerText = sentImage ? "Fotoğrafa bakıyorum Reis... 🔍" : "Düşünüyorum Reis... ⏳";
            setRobotThinking(true, sentImage);
            
            fetch("/chat", { 
                method: "POST", 
                headers: {"Content-Type": "application/json"}, 
                body: JSON.stringify({ 
                    message: promptText, 
                    history: chatHistory, 
                    chat_file: currentChatFile, 
                    is_online: isOnline, 
                    image: sentImage 
                }) 
            })
            .then(res => res.json())
            .then(data => {
                setRobotThinking(false);
                let reply = data.response;
                if(data.chat_file) currentChatFile = data.chat_file;
                chatHistory.push({sender: "user", text: promptText ? promptText : "[Fotoğraf Gönderildi]"});
                chatHistory.push({sender: "bot", text: reply});
                renderChat();
                speakSlowlyAndType(reply);
            })
            .catch(() => {
                setRobotThinking(false);
                speakSlowlyAndType("Buradayım Reis!");
            });
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
                files.forEach(f=>{ 
                    let selected = (f === currentChatFile) ? "selected" : "";
                    s.innerHTML += `<option value="${f}" ${selected}>${f}</option>`; 
                });
            });
        }
        loadChatList();

        function loadChat(filename) {
            if(!filename) return;
            currentChatFile = filename;
            fetch('/get_chat/' + filename).then(r=>r.json()).then(data=>{
                chatHistory = data;
                renderChat();
                if(isRobotActive) {
                    speakSlowlyAndType("Eski sohbet yüklendi Reis!");
                }
            });
        }

        function renderChat() {
            let chat = document.getElementById("chatbox");
            chat.innerHTML = "";
            chatHistory.forEach((h, idx)=>{
                if(h.sender === 'user') {
                    chat.innerHTML += `<div class="msg-user"><b>Sen:</b> ${h.text}</div>`;
                } else {
                    let msgId = "msg-" + idx;
                    chat.innerHTML += `
                        <div class="msg-bot">
                            <b>MUHAMMED ALİ AI:</b> <span id="${msgId}">${h.text}</span>
                            <div class="audio-controls">
                                <button class="btn-audio" onclick="speakTextById('${msgId}')">🔊 Sesli Oku</button>
                                <button class="btn-audio" onclick="stopSpeech()">⏹️ Durdur</button>
                                <button class="btn-audio" onclick="copyTextById('${msgId}')">📋 Kopyala</button>
                            </div>
                        </div>`;
                }
            });
            chat.scrollTop = chat.scrollHeight;
        }

        function speakTextById(id) {
            let elem = document.getElementById(id);
            if(elem) speakText(elem.innerText);
        }

        function copyTextById(id) {
            let elem = document.getElementById(id);
            if(elem) {
                let cleanText = elem.innerText.replace(/<[^>]*>?/gm, '');
                navigator.clipboard.writeText(cleanText).then(() => {
                    alert("Metin panoya kopyalandı Reis! 📋");
                });
            }
        }

        function speakText(text) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                let cleanText = text.replace(/<[^>]*>?/gm, '');
                let utter = new SpeechSynthesisUtterance(cleanText);
                utter.lang = 'tr-TR';
                utter.rate = 0.85;
                window.speechSynthesis.speak(utter);
            }
        }

        function stopSpeech() {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
            }
        }

        function startVoice(targetInputId) {
            let Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
            if(!Speech) return alert("Ses tanıma desteklenmiyor Reis.");
            let rec = new Speech();
            rec.lang = 'tr-TR';
            rec.start();
            rec.onresult = function(e) {
                document.getElementById(targetInputId).value = e.results[0][0].transcript;
            };
        }

        function startVoiceAndSendCam() {
            let Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
            if(!Speech) return alert("Ses tanıma desteklenmiyor Reis.");
            let rec = new Speech();
            rec.lang = 'tr-TR';
            rec.start();
            document.getElementById("camStatus").innerText = "Dinliyorum Reis... 🎙️";
            rec.onresult = function(e) {
                let voiceText = e.results[0][0].transcript;
                document.getElementById("camInput").value = voiceText;
                sendCamMsg(false);
            };
        }

        function sendMsg(isDirectImage = false) {
            let input = document.getElementById("userInput");
            let msg = isDirectImage ? "" : input.value.trim();
            let sentImage = selectedChatBase64Image;

            if (!msg && !sentImage) return;

            input.value = "";
            clearChatImage();

            let chat = document.getElementById("chatbox");
            let userDisplay = msg;
            if (sentImage) {
                userDisplay += `<br><img src="${sentImage}" style="max-width:180px; border-radius:10px; margin-top:6px;">`;
            }
            chat.innerHTML += `<div class='msg-user'><b>Sen:</b> ${userDisplay}</div>`;
            
            let loadingId = "load-" + Date.now();
            chat.innerHTML += `<div class='msg-bot' id='${loadingId}'>Yazıyor... <span id="timer-${loadingId}">0.0s</span> ⏳</div>`;
            chat.scrollTop = chat.scrollHeight;

            setRobotThinking(true, sentImage);

            let startTime = performance.now();
            let timerInterval = setInterval(() => {
                let elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
                let timerElem = document.getElementById(`timer-${loadingId}`);
                if(timerElem) timerElem.innerText = `${elapsed}s`;
            }, 100);

            fetch("/chat", { 
                method: "POST", 
                headers: {"Content-Type": "application/json"}, 
                body: JSON.stringify({ 
                    message: msg, 
                    history: chatHistory, 
                    chat_file: currentChatFile, 
                    is_online: isOnline,
                    image: sentImage
                }) 
            })
            .then(res => res.json())
            .then(data => { 
                clearInterval(timerInterval);
                setRobotThinking(false);
                let duration = ((performance.now() - startTime) / 1000).toFixed(2);

                let reply = data.response;
                if(data.chat_file) currentChatFile = data.chat_file;

                chatHistory.push({sender: "user", text: userDisplay});
                chatHistory.push({sender: "bot", text: reply});

                let loadingElem = document.getElementById(loadingId);
                let replyId = "reply-" + Date.now();
                loadingElem.innerHTML = `
                    <b>MUHAMMED ALİ AI:</b> <span id="${replyId}">${reply}</span> 
                    <span class="timer-badge">⏱️ ${duration} saniyede yanıtlandı</span>
                    <div class="audio-controls">
                        <button class="btn-audio" onclick="speakTextById('${replyId}')">🔊 Sesli Oku</button>
                        <button class="btn-audio" onclick="stopSpeech()">⏹️ Durdur</button>
                        <button class="btn-audio" onclick="copyTextById('${replyId}')">📋 Kopyala</button>
                    </div>`;
                chat.scrollTop = chat.scrollHeight;
                
                if(isRobotActive) {
                    speakSlowlyAndType(reply);
                } else {
                    speakText(reply);
                }
                loadChatList();
            })
            .catch(() => {
                clearInterval(timerInterval);
                setRobotThinking(false);
                document.getElementById(loadingId).innerText = "Buradayım Reis!";
            });
        }

        function sendCamMsg(isDirect) {
            let input = document.getElementById("camInput");
            let msg = isDirect ? "" : input.value.trim();
            input.value = "";
            
            document.getElementById("camStatus").innerText = "Bakıyorum Reis... ⏳";
            document.getElementById("camAudioControls").style.display = "none";

            let imageData = null;
            let video = document.getElementById("webcam");
            if (videoStream) {
                let canvas = document.getElementById("camCanvas");
                canvas.width = video.videoWidth || 640;
                canvas.height = video.videoHeight || 480;
                let ctx = canvas.getContext("2d");
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                imageData = canvas.toDataURL("image/jpeg");
            }

            setRobotThinking(true, imageData);

            fetch("/chat", { 
                method: "POST", 
                headers: {"Content-Type": "application/json"}, 
                body: JSON.stringify({ message: msg, history: [], image: imageData, is_online: isOnline }) 
            })
            .then(res => res.json())
            .then(data => {
                setRobotThinking(false);
                document.getElementById("camStatus").innerHTML = "<b>MUHAMMED ALİ AI:</b> " + data.response;
                document.getElementById("camAudioControls").style.display = "flex";
                if(isRobotActive) {
                    speakSlowlyAndType(data.response);
                } else {
                    speakText(data.response);
                }
            })
            .catch(() => {
                setRobotThinking(false);
                document.getElementById("camStatus").innerText = "Buradayım Reis!";
            });
        }

        function newChat() {
            chatHistory = [];
            currentChatFile = null;
            clearChatImage();
            document.getElementById("chatbox").innerHTML = "<div class='msg-bot'>Yeni sohbet açıldı Reis!</div>";
        }

        function startCam() {
            stopCam();
            navigator.mediaDevices.getUserMedia({ video: { facingMode: facingMode } })
                .then(stream => { 
                    videoStream = stream;
                    document.getElementById("webcam").srcObject = stream; 
                    document.getElementById("camStatus").innerText = "Kamera aktif Reis.";
                })
                .catch(err => alert("Kamera açılamadı Reis!"));
        }

        function switchCam() {
            facingMode = (facingMode === "user") ? "environment" : "user";
            startCam();
        }

        function stopCam() {
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
                document.getElementById("webcam").srcObject = null;
                document.getElementById("camStatus").innerText = "Kamera kapatıldı Reis.";
            }
        }

        function uploadImage() {
            let fileInput = document.getElementById('fileInput');
            if (fileInput.files.length === 0) return;
            
            let formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/upload', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                if(data.success) {
                    loadGallery();
                } else {
                    alert("Yüklenemedi Reis.");
                }
            });
        }

        function loadGallery() {
            fetch('/get_gallery').then(r=>r.json()).then(files=>{
                let grid = document.getElementById("galleryGrid");
                grid.innerHTML = "";
                if(files.length === 0) { grid.innerHTML = "<p style='grid-column: span 2;'>Fotoğraf yok Reis.</p>"; return; }
                files.forEach(f=>{
                    grid.innerHTML += `
                        <div class="gallery-card">
                            <img src="/uploads/${f}">
                            <a class="btn-dl" href="/uploads/${f}" download>📥 İndir</a>
                        </div>`;
                });
            });
        }
    </script>
</body>
</html>"""


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
  return jsonify(
      [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
  )


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

  filename = secure_filename(
      f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
  )
  filepath = os.path.join(UPLOAD_FOLDER, filename)
  file.save(filepath)
  return jsonify({
      'success': True,
      'filename': filename,
      'url': f'/uploads/{filename}',
  })


@app.route('/chat', methods=['POST'])
def chat():
  chat_file = None
  try:
    req_data = request.json or {}
    user_msg = req_data.get('message', '')
    history = req_data.get('history', [])
    chat_file = req_data.get('chat_file')
    is_online = req_data.get('is_online', True)
    image_data = req_data.get('image')

    saved_image_url = None
    if image_data and image_data.startswith('data:image'):
      try:
        header, encoded = image_data.split(',', 1)
        file_ext = 'png' if 'png' in header else 'jpg'
        img_bytes = base64.b64decode(encoded)
        img_name = (
            f"chat_img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        )
        img_path = os.path.join(UPLOAD_FOLDER, img_name)
        with open(img_path, 'wb') as f:
          f.write(img_bytes)
        saved_image_url = f'{request.host_url.rstrip("/")}/uploads/{img_name}'
      except Exception as e_img:
        print('Görsel Kayıt Hatası:', e_img)
        saved_image_url = image_data
    elif image_data:
      saved_image_url = image_data

    if not is_online:
      reply = f"Çevrimdışıyız Reis! Mesaj: '{user_msg}'"
    else:
      reply = ask_ai_engine(user_msg, history, image_data=saved_image_url)

    if not chat_file:
      chat_file = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    filepath = os.path.join(CHATS_FOLDER, chat_file)
    history.append(
        {'sender': 'user', 'text': user_msg if user_msg else '[Görsel Gönderildi]'}
    )
    history.append({'sender': 'bot', 'text': reply})
    with open(filepath, 'w', encoding='utf-8') as f:
      json.dump(history, f, ensure_ascii=False, indent=2)

    return jsonify({'response': reply, 'chat_file': chat_file})
  except Exception as general_e:
    print('GENEL HATA:', general_e)
    return jsonify({
        'response': (
            'Hayrola Reis, bağlantıda ufak bir kilitlenme oldu ama buradayım'
            ' kanka!'
        ),
        'chat_file': chat_file,
    })


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
