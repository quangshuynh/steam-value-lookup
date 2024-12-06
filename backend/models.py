from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(20), unique=True, nullable=True)
    username = db.Column(db.String(100))