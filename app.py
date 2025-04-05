from flask import Flask, request, jsonify, render_template
import os
import speech_recognition as sr
from pydub import AudioSegment
import language_tool_python
from models import db, Analysis
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analyses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
tool = language_tool_python.LanguageTool('en-US')

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'wav', 'mp3'}

def audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data)
    return text

def analyze_grammar(text):
    matches = tool.check(text)
    error_details = [{
        'ruleId': m.ruleId,
        'message': m.message,
        'replacements': m.replacements,
        'context': m.context
    } for m in matches]
    
    error_count = len(matches)
    word_count = len(text.split())
    score = max(0, 100 - (error_count / max(1, word_count)) * 100)
    
    if score > 90:
        feedback = "Excellent grammar!"
    elif score > 80:
        feedback = "Good job!"
    elif score > 60:
        feedback = "Needs some improvement"
    else:
        feedback = "Needs significant improvement"
    
    return {
        'score': round(score),
        'feedback': feedback,
        'transcription': text,
        'errors': error_details
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/history')
def history():
    analyses = Analysis.query.order_by(Analysis.timestamp.desc()).limit(10).all()
    return render_template('history.html', analyses=analyses)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type (use .wav or .mp3)'}), 400

    try:
        # Save and convert audio
        temp_path = secure_filename('temp_audio.wav')
        file.save(temp_path)
        if file.filename.endswith('.mp3'):
            audio = AudioSegment.from_mp3(temp_path)
            audio.export(temp_path, format='wav')

        # Process audio
        text = audio_to_text(temp_path)
        analysis_result = analyze_grammar(text)

        # Save to database
        new_analysis = Analysis(
            score=analysis_result['score'],
            transcription=analysis_result['transcription'],
            feedback=analysis_result['feedback'],
            errors=analysis_result['errors']
        )
        db.session.add(new_analysis)
        db.session.commit()

        # Clean up
        os.remove(temp_path)

        return jsonify(analysis_result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)