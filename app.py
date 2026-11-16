# 🔑 API ANAHTARI YAPILANDIRMASI
API_KEYS = [
    {
        "type": "groq",
        "key": "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",
    }
]

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

    models_to_try = [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant',
        'llama3-70b-8192',
        'llama3-8b-8192'
    ]

    for item in API_KEYS:
        ak = item["key"]
        try:
            client = Groq(api_key=ak)
            for model_name in models_to_try:
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
