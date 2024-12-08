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
        return render_template('index.html', error="Please provide a valid SteamID")

    try:
        user_data = get_owned_games(steam_id)

        # sort games by playtime in descending order
        if 'games' in user_data['response']:
            games = user_data['response']['games']

            # sort games by playtime in descending order
            sorted_games = sorted(games, key=lambda game: game.get('playtime_forever', 0), reverse=True)
            
            # calculate statistics
            total_games = len(games)
            total_playtime_minutes = sum(game.get('playtime_forever', 0) for game in games)
            total_playtime_hours = round(total_playtime_minutes / 60, 2)
            average_playtime_hours = round(total_playtime_hours / total_games, 2) if total_games > 0 else 0

            # dummy value for game prices (replace with real data if available)
            total_value = round(sum(game.get('value', 0) for game in games), 2)

            # add calculated statistics to user_data
            user_data['statistics'] = {
                'total_games': total_games,
                'total_playtime_hours': total_playtime_hours,
                'average_playtime_hours': average_playtime_hours,
                'total_value': total_value
            }

            user_data['response']['games'] = sorted_games

        return render_template('results.html', user_data=user_data)

    except ValueError as e:
        return render_template('index.html', error=str(e))
    except requests.exceptions.HTTPError as e:
        return render_template('index.html', error="Failed to fetch data from Steam API.")


if __name__ == "__main__":
    app.run(debug=True)
