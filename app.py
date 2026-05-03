from flask import Flask, request, jsonify, Response
from groq import Groq
from gtts import gTTS
from langdetect import detect
import os, datetime, io, urllib.request

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

    if any(w in text for w in ["play", "bajao", "song", "gaana", "music"]):
        query = text
        for w in ["play", "bajao", "song", "gaana", "music", "chalaao", "baja", "bajado"]:
            query = query.replace(w, "")
        query = query.strip()
        if not query:
            query = "top hindi songs"
        return {"type": "play_song", "query": query}

    if any(w in text for w in ["search", "dhundo", "khojo"]):
        query = text.replace("search", "").replace("dhundo", "").replace("khojo", "").strip()
        if query:
            return {"type": "open_url", "url": f"https://www.google.com/search?q={query}"}

    return None

def ask_milo(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=150,
        messages=[{
            "role": "system",
            "content": """You are Milo V2, a smart AI assistant like Jarvis.
Reply in the SAME language the user speaks.
Support: English, Hindi, Gujarati, Marathi.
Keep replies SHORT - max 2 sentences only!
Never repeat yourself."""
        }] + conversation_history
    )
    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

def make_audio(text, lang):
    tts = gTTS(text=text, lang=lang, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

def get_youtube_video_id(query):
    try:
        search_url = f"https://www.youtube.com/results?search_query={query}"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        html = response.read().decode()
        start = html.find('"videoId":"') + 11
        video_id = html[start:start+11]
        return video_id
    except:
        return None

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
        elif command_result['type'] == 'play_song':
            query = command_result.get('query', 'top hindi songs')
            video_id = get_youtube_video_id(query)
            reply = f"Playing {query} for you!"
            return jsonify({
                'reply': reply,
                'lang': 'en',
                'action': 'play_song',
                'video_id': video_id
            })
        elif command_result['type'] == 'info':
            return jsonify({
                'reply': command_result['response'],
                'lang': 'en'
            })

    reply = ask_milo(user_input)
    lang = detect_language(reply)
    return jsonify({'reply': reply, 'lang': lang})

@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    try:
        audio_bytes = make_audio(text, lang)
        return Response(audio_bytes, mimetype='audio/mpeg')
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)