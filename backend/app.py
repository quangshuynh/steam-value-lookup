from flask import Flask, render_template, request
from config import Config
from database import init_db, db
from steam_api import get_owned_games, get_player_summaries, vanity_url, get_game_value_parallel
# from models import User, Game, InventoryItem
import requests

app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lookup', methods=['POST'])
def lookup():
    steamid_entry = request.form.get('steam_id')
    if not steamid_entry:
        return render_template('index.html', error="Please provide a valid SteamID")

    try:
        # vanity names
        if not steamid_entry.isdigit():
            steam_id = vanity_url(steamid_entry)
        else:
            steam_id = steamid_entry

        user_data = get_owned_games(steam_id)

        # player info
        player_data = get_player_summaries(steam_id)
        if 'players' in player_data['response'] and player_data['response']['players']:
            player = player_data['response']['players'][0]
            user_data['player'] = {
                'steamid': player.get('steamid'),
                'name': player.get('personaname'),
                'profile_url': player.get('profileurl'),
                'avatar': player.get('avatar'),
                'avatar_medium': player.get('avatarmedium'),
                'avatar_full': player.get('avatarfull')
            }

        # sort games by playtime in descending order by default
        if 'games' in user_data['response']:
            games = user_data['response']['games'] 
            app_ids = [game['appid'] for game in games]

            # total value
            prices = get_game_value_parallel(app_ids)
            total = 0.0
            for game in games:
                app_id = game['appid']
                game['value'] = prices.get(app_id, 0.0)
                total += game['value']

            # sort games by playtime in descending order
            sorted_games = sorted(games, key=lambda game: game.get('playtime_forever', 0), reverse=True)


            # calculate stats
            total_games = len(games)
            total_playtime_minutes = sum(game.get('playtime_forever', 0) for game in games)
            total_playtime_hours = round(total_playtime_minutes / 60, 2)
            average_playtime_hours = round(total_playtime_hours / total_games, 2) if total_games > 0 else 0
            total_value = round(total, 2)

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
