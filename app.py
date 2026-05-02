from flask import Flask, request, jsonify, Response
from groq import Groq
from gtts import gTTS
from langdetect import detect
import tempfile, os, datetime, io

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
conversation_history = []

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
    if any(w in text for w in ["time", "samay", "vakt", "kitne baje"]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"type": "info", "response": f"Current time is {now}"}
    if any(w in text for w in ["date", "aaj", "tarikh", "today"]):
        today = datetime.datetime.now().strftime("%A, %d %B %Y")
        return {"type": "info", "response": f"Today is {today}"}
    if any(w in text for w in ["weather", "mausam", "havaman"]):
        return {"type": "open_url", "url": "https://weather.com"}
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
Be smart, helpful, friendly and concise."""
        }] + conversation_history
    )
    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

def make_audio_bytes(reply, lang):
    tts = gTTS(text=reply, lang=lang, slow=False)
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    return audio_buffer.read()

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
            return jsonify({
                'reply': reply,
                'lang': lang,
                'action': 'open_url',
                'url': command_result['url']
            })
        elif command_result['type'] == 'info':
            reply = command_result['response']
            return jsonify({'reply': reply, 'lang': 'en'})

    reply = ask_milo(user_input)
    lang = detect_language(reply)
    return jsonify({'reply': reply, 'lang': lang})

@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    try:
        audio_bytes = make_audio_bytes(text, lang)
        return Response(audio_bytes, mimetype='audio/mpeg')
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
