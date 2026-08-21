from flask import Flask

from database import db, init_db
from models import Game, InventoryItem, User


def test_database_initialization_and_model_round_trip():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    init_db(app)

    with app.app_context():
        user = User(
            steam_id="76561198000000000",
            username="Test Player",
            profile_url="https://steamcommunity.com/id/test-player/",
        )
        db.session.add(user)
        db.session.flush()

        game = Game(user_id=user.id, name="Test Game", playtime=120, value=12.99)
        db.session.add(game)
        db.session.flush()
        db.session.add(InventoryItem(user_id=user.id, game_id=game.id, name="Item", value=1.25))
        db.session.commit()

        stored_user = db.session.execute(db.select(User)).scalar_one()
        stored_game = db.session.execute(db.select(Game)).scalar_one()
        stored_item = db.session.execute(db.select(InventoryItem)).scalar_one()

        assert stored_user.username == "Test Player"
        assert stored_game.value == 12.99
        assert stored_item.game_id == stored_game.id

        db.session.remove()
        db.drop_all()
