from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Float)
    transcription = db.Column(db.Text)
    feedback = db.Column(db.Text)
    errors = db.Column(db.JSON)

    def __repr__(self):
        return f'<Analysis {self.id} - Score: {self.score}>'