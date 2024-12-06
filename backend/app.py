from flask import Flask, render_template, request
from config import Config
from database import init_db, db
from steam_api import get_owned_games, get_inventory
from models import User, Game, InventoryItem
import requests

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
        return render_template('index.html', error="Please provide a valid SteamID or Vanity URL.")

    try:
        user_data = get_owned_games(steam_id)

        # sort games by playtime in descending order
        if 'games' in user_data['response']:
            user_data['response']['games'] = sorted(
                user_data['response']['games'], key=lambda game: game['playtime_forever'], reverse=True
            )

        return render_template('results.html', user_data=user_data)
    except ValueError as e:
        return render_template('index.html', error=str(e))
    except requests.exceptions.HTTPError as e:
        return render_template('index.html', error="Failed to fetch data from Steam API.")


if __name__ == "__main__":
    app.run(debug=True)
