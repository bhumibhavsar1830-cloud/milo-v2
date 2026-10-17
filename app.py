from flask import Flask, request, jsonify, Response
from groq import Groq, APIStatusError, APIConnectionError, RateLimitError
from gtts import gTTS
from langdetect import detect
from urllib.parse import quote_plus
import os
import datetime
import io
import urllib.request
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Set GROQ_API_KEY in Render Environment Variables.
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

MODEL_NAME = "openai/gpt-oss-120b"
MAX_HISTORY_MESSAGES = 20
conversation_history = []

SYSTEM_PROMPT = """Your Milo V2, a smart AI assistant like Jarvis Made By Bhumi.
Reply in the SAME language the user speaks.
Support English, Hindi, Gujarati, and Marathi.
Keep replies SHORT - max 2 sentences only!
Never repeat yourself."""

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
        if lang in ("hi", "gu", "mr"):
            return lang
        return "en"
    except Exception:
        return "en"


def check_commands(user_input):
    text = user_input.lower().strip()

    for command, url in APP_COMMANDS.items():
        if command in text:
            return {"type": "open_url", "url": url}

    if any(w in text for w in [
        "time", "samay", "vakt", "kitne baje"
    ]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {
            "type": "info",
            "response": f"Current time is {now}"
        }

    if any(w in text for w in [
        "date", "aaj", "tarikh", "today"
    ]):
        today = datetime.datetime.now().strftime(
            "%A, %d %B %Y"
        )
        return {
            "type": "info",
            "response": f"Today is {today}"
        }

    if any(w in text for w in [
        "weather", "mausam", "havaman"
    ]):
        return {
            "type": "open_url",
            "url": "https://weather.com"
        }

    if any(w in text for w in [
        "play", "bajao", "song", "gaana", "music"
    ]):
        query = text
        for word in [
            "play", "bajao", "song", "gaana",
            "music", "chalaao", "baja", "bajado"
        ]:
            query = query.replace(word, "")

        query = query.strip() or "top hindi songs"

        return {
            "type": "play_song",
            "query": query
        }

    if any(w in text for w in [
        "search", "dhundo", "khojo"
    ]):
        query = text
        for word in ["search", "dhundo", "khojo"]:
            query = query.replace(word, "")

        query = query.strip()
        if query:
            return {
                "type": "open_url",
                "url": (
                    "https://www.google.com/search?q="
                    + quote_plus(query)
                )
            }

    return None


def ask_milo(user_input):
    if not client:
        raise RuntimeError(
            "GROQ_API_KEY is not configured on the server."
        )

    # Keep a bounded history so requests don't grow forever.
    history = conversation_history[-MAX_HISTORY_MESSAGES:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history + [
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=messages
    )

    reply = response.choices[0].message.content

    if not reply:
        raise RuntimeError("The AI returned an empty response.")

    conversation_history.extend([
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": reply}
    ])

    # Retain only the latest messages.
    del conversation_history[:-MAX_HISTORY_MESSAGES]

    return reply


def make_audio(text, lang):
    tts = gTTS(text=text, lang=lang, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def get_youtube_video_id(query):
    try:
        search_url = (
            "https://www.youtube.com/results?search_query="
            + quote_plus(query)
        )
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode(
                "utf-8", errors="ignore"
            )

        marker = '"videoId":"'
        start = html.find(marker)

        if start == -1:
            return None

        start += len(marker)
        video_id = html[start:start + 11]

        if len(video_id) == 11:
            return video_id

        return None

    except Exception:
        app.logger.exception("YouTube lookup failed")
        return None


@app.route("/")
def home():
    try:
        with open("index.html", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        app.logger.exception("index.html not found")
        return jsonify({
            "error": "Website file is missing."
        }), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "ai_configured": client is not None
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "")

    if not isinstance(user_input, str) or not user_input.strip():
        return jsonify({
            "error": "Please enter a message."
        }), 400

    user_input = user_input.strip()

    if len(user_input) > 10000:
        return jsonify({
            "error": "Message is too long."
        }), 400

    command_result = check_commands(user_input)

    try:
        if command_result:
            command_type = command_result["type"]

            if command_type == "info":
                return jsonify({
                    "reply": command_result["response"],
                    "lang": detect_language(
                        command_result["response"]
                    )
                })

            if command_type == "play_song":
                query = command_result.get(
                    "query", "top hindi songs"
                )
                video_id = get_youtube_video_id(query)

                return jsonify({
                    "reply": f"Playing {query} for you!",
                    "lang": "en",
                    "action": "play_song",
                    "video_id": video_id
                })

            if command_type == "open_url":
                reply = ask_milo(user_input)

                return jsonify({
                    "reply": reply,
                    "lang": detect_language(reply),
                    "action": "open_url",
                    "url": command_result["url"]
                })

        reply = ask_milo(user_input)

        return jsonify({
            "reply": reply,
            "lang": detect_language(reply)
        })

    except RateLimitError:
        app.logger.exception("Groq rate limit reached")
        return jsonify({
            "error": (
                "Milo is busy right now. Please try again shortly."
            )
        }), 429

    except APIStatusError as e:
        app.logger.exception("Groq API returned an error")

        # Keep technical details in server logs, not the browser.
        return jsonify({
            "error": (
                "Milo AI service returned an error. "
                "Please try again later."
            )
        }), 502

    except APIConnectionError:
        app.logger.exception("Could not connect to Groq")
        return jsonify({
            "error": "Could not connect to Milo AI. Try again."
        }), 502

    except Exception:
        app.logger.exception("Unexpected /chat error")
        return jsonify({
            "error": "Something went wrong. Please try again."
        }), 500


@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    lang = data.get("lang", "en")

    if not isinstance(text, str) or not text.strip():
        return jsonify({
            "error": "Text is required."
        }), 400

    if lang not in ("en", "hi", "gu", "mr"):
        lang = "en"

    try:
        audio_bytes = make_audio(text, lang)
        return Response(
            audio_bytes,
            mimetype="audio/mpeg"
        )
    except Exception:
        app.logger.exception("Text-to-speech failed")
        return jsonify({
            "error": "Audio generation failed."
        }), 500


if __name__ == "__main__":
    # Production deployments should use Gunicorn.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
    
