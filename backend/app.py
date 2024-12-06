from flask import Flask, render_template, request
from config import Config
from database import init_db, db
from steam_api import get_owned_games, get_inventory
from models import User, Game, InventoryItem

app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lookup', methods=['POST'])
def lookup():
    steam_id = request.form.get('steam_id')
    if not steam_id:
        return render_template('index.html', error="Please provide a valid SteamID.")

    user_data = get_owned_games(steam_id)
    # parse and save to database (or return to render)
    # example: Save user, games, and inventory in the database
    return render_template('results.html', user_data=user_data)

if __name__ == "__main__":
    app.run(debug=True)
