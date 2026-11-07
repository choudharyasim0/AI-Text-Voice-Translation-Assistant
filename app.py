import os

from flask import Flask, jsonify, render_template, request, send_file

from config import Config
from services.languages import LanguageService
from services.ocr import OCRService
from services.speech import SpeechService
from services.translator import TranslationError, TranslatorService

app = Flask(__name__)
app.config.from_object(Config)


def _initialize_services():
    """Keep import-time filesystem/setup failures from preventing Flask startup."""
    try:
        translation_service = TranslatorService(app.config.get('HISTORY_FILE', '/tmp/history.json'))
    except Exception:
        app.logger.exception('Translator initialization failed')
        translation_service = None
    try:
        speech_service = SpeechService(app.config.get('AUDIO_FOLDER'))
    except Exception:
        app.logger.exception('Speech service initialization failed')
        speech_service = None
    return translation_service, speech_service


translator, speech = _initialize_services()
# OCR model initialization is lazy inside OCRService, so app import does not load it.
ocr_service = OCRService()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/languages')
def languages():
    try:
        return jsonify(LanguageService.get_languages())
    except Exception:
        app.logger.exception('Language listing failed')
        return jsonify({'auto': 'Auto Detect', 'en': 'English'}), 200


@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'A JSON object is required.'}), 400
    text = data.get('text')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'success': False, 'error': 'Text is required.'}), 400
    source = data.get('source') or 'auto'
    target = data.get('target') or 'en'
    if not isinstance(source, str) or not isinstance(target, str):
        return jsonify({'success': False, 'error': 'Invalid language selection.'}), 400
    if translator is None:
        return jsonify({'success': False, 'error': 'Translation service is unavailable.'}), 503
    try:
        result = translator.translate(text, source, target, save_history=data.get('save_history', True))
        return jsonify({'success': True, 'translation': result})
    except TranslationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 502
    except Exception:
        app.logger.exception('Translation request failed')
        return jsonify({'success': False, 'error': 'Translation request failed.'}), 500


@app.route('/translate-image', methods=['POST'])
def translate_image():
    """Extract text from an uploaded image and translate it."""
    if translator is None:
        return jsonify({'success': False, 'error': 'Translation service is unavailable.'}), 503

    image = request.files.get('image')
    if image is None or not image.filename:
        return jsonify({'success': False, 'error': 'Please select an image.'}), 400
    if image.mimetype and not image.mimetype.startswith('image/'):
        return jsonify({'success': False, 'error': 'The uploaded file must be an image.'}), 400

    try:
        image_bytes = image.stream.read(OCRService.MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > OCRService.MAX_IMAGE_BYTES:
            return jsonify({'success': False, 'error': 'Image exceeds the 8 MB upload limit.'}), 413

        source = request.form.get('source', 'auto').strip() or 'auto'
        target = request.form.get('target', 'en').strip() or 'en'
        extracted_text = ocr_service.extract_text(image_bytes)
        translated_text = translator.translate(extracted_text, source, target)
        return jsonify({
            'success': True,
            'extracted_text': extracted_text,
            'translation': translated_text,
        })
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception:
        app.logger.exception('Image translation failed')
        return jsonify({
            'success': False,
            'error': 'Could not extract or translate text from this image.',
        }), 502


@app.route('/history')
def history():
    if translator is None:
        return jsonify([])
    try:
        return jsonify(translator.get_history())
    except Exception:
        app.logger.exception('History retrieval failed')
        return jsonify([])


@app.route('/clear-history', methods=['DELETE'])
def clear_history():
    if translator is None:
        return jsonify({'success': True})
    try:
        translator.clear_history()
        return jsonify({'success': True})
    except Exception:
        app.logger.exception('History clearing failed')
        return jsonify({'success': False, 'error': 'Could not clear history.'}), 500


@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'A JSON object is required.'}), 400
    text = data.get('text')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'success': False, 'error': 'Text is required.'}), 400
    lang = data.get('lang') or 'en'
    if not isinstance(lang, str):
        return jsonify({'success': False, 'error': 'Invalid language selection.'}), 400
    if speech is None:
        return jsonify({'success': False, 'error': 'Speech service is unavailable.'}), 503
    try:
        buffer = speech.generate_audio(text, lang)
        return send_file(buffer, mimetype='audio/mpeg', as_attachment=False, download_name='speech.mp3')
    except Exception:
        app.logger.exception('Text-to-speech request failed')
        return jsonify({'success': False, 'error': 'Text-to-speech generation failed.'}), 502


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
