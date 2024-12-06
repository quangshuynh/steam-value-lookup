from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(100))
    profile_url = db.Column(db.String(200))

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200))
    playtime = db.Column(db.Integer)
    value = db.Column(db.Float)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    name = db.Column(db.String(200))
    value = db.Column(db.Float)