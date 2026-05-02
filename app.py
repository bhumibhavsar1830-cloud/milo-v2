from flask import Flask, request, jsonify, send_file
from groq import Groq
from gtts import gTTS
from langdetect import detect
import tempfile, os, datetime

app = Flask(__name__)
import os
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
conversation_history = []
audio_files = {}

APP_COMMANDS = {
    "open gmail": "https://mail.google.com",
    "open youtube": "https://youtube.com",
    "open whatsapp": "https://web.whatsapp.com",
    "open google": "https://google.com",
    "open maps": "https://maps.google.com",
    "open instagram": "https://instagram.com",
    "open facebook": "https://facebook.com",
    "open netflix": "https://netflix.com",
    "open spotify": "https://open.spotify.com",
    "open twitter": "https://twitter.com",
    "gmail kholo": "https://mail.google.com",
    "youtube kholo": "https://youtube.com",
    "whatsapp kholo": "https://web.whatsapp.com",
    "google kholo": "https://google.com",
    "instagram kholo": "https://instagram.com",
    "gmail ughad": "https://mail.google.com",
    "youtube ughad": "https://youtube.com",
    "whatsapp ughad": "https://web.whatsapp.com",
}

def detect_language(text):
    try:
        lang = detect(text)
        if lang == 'hi': return 'hi'
        elif lang == 'gu': return 'gu'
        elif lang == 'mr': return 'mr'
        else: return 'en'
    except:
        return 'en'

def check_commands(user_input):
    text = user_input.lower()
    for command, url in APP_COMMANDS.items():
        if command in text:
            return {"type": "open_url", "url": url}
    if any(w in text for w in ["time", "samay", "vakt", "kel kiti", "kitne baje"]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"type": "info", "response": f"Current time is {now}"}
    if any(w in text for w in ["date", "aaj", "tarikh", "today", "konchi tarikh"]):
        today = datetime.datetime.now().strftime("%A, %d %B %Y")
        return {"type": "info", "response": f"Today is {today}"}
    if any(w in text for w in ["weather", "mausam", "havaman"]):
        return {"type": "open_url", "url": "https://weather.com"}
    if any(w in text for w in ["search", "dhundo", "khojo"]):
        query = text.replace("search", "").replace("dhundo", "").replace("khojo", "").strip()
        return {"type": "open_url", "url": f"https://www.google.com/search?q={query}"}
    return None

def ask_milo(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=500,
        messages=[{
            "role": "system",
            "content": """You are Milo V2, an advanced AI assistant like Jarvis.
You support English, Hindi, Gujarati, Marathi.
Always reply in the same language the user speaks.
Be smart, helpful, friendly and concise.
You can open apps, search web, answer questions, tell time and date."""
        }] + conversation_history
    )
    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

def make_audio(reply, lang):
    tts = gTTS(text=reply, lang=lang, slow=False)
    temp_audio = tempfile.mktemp(suffix='.mp3')
    tts.save(temp_audio)
    audio_id = os.path.basename(temp_audio)
    audio_files[audio_id] = temp_audio
    return audio_id

@app.route('/')
def home():
    return open('index.html', encoding='utf-8').read()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    command_result = check_commands(user_input)

    if command_result:
        if command_result['type'] == 'open_url':
            reply = ask_milo(user_input)
            lang = detect_language(reply)
            audio_id = make_audio(reply, lang)
            return jsonify({'reply': reply, 'audio_id': audio_id, 'lang': lang, 'action': 'open_url', 'url': command_result['url']})
        elif command_result['type'] == 'info':
            reply = command_result['response']
            audio_id = make_audio(reply, 'en')
            return jsonify({'reply': reply, 'audio_id': audio_id, 'lang': 'en'})

    reply = ask_milo(user_input)
    lang = detect_language(reply)
    audio_id = make_audio(reply, lang)
    return jsonify({'reply': reply, 'audio_id': audio_id, 'lang': lang})

@app.route('/audio/<audio_id>')
def audio(audio_id):
    if audio_id in audio_files:
        path = audio_files[audio_id]
        if os.path.exists(path):
            return send_file(path, mimetype='audio/mpeg')
    return "Not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
