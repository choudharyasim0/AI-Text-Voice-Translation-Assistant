import os

from flask import Flask, jsonify, render_template, request, send_file

from config import Config
from services.languages import LanguageService
from services.speech import SpeechService
from services.translator import TranslatorService

app = Flask(__name__)
app.config.from_object(Config)

translator = TranslatorService(app.config["HISTORY_FILE"])
speech = SpeechService(app.config["AUDIO_FOLDER"])


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/languages")
def languages():
    return jsonify(LanguageService.get_languages())


@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        source = data.get("source") or "auto"
        target = data.get("target") or "en"
        save_history = data.get("save_history", True)

        if not text:
            return jsonify({"success": False, "error": "Text is required."}), 400

        translated = translator.translate(text, source, target, save_history=save_history)
        return jsonify({"success": True, "translation": translated})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/history")
def history():
    try:
        return jsonify(translator.get_history())
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/clear-history", methods=["DELETE"])
def clear_history():
    try:
        translator.clear_history()
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        lang = data.get("lang") or "en"

        if not text:
            return jsonify({"success": False, "error": "Text is required."}), 400

        audio_file = speech.generate_audio(text, lang)
        return send_file(audio_file, mimetype="audio/mpeg", as_attachment=False)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
