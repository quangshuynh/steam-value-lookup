from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, render_template, request
from config import Config
from database import init_db, db
from steam_api import (
    get_achievement_summaries,
    get_game_value_parallel,
    get_inventory_values,
    get_owned_games,
    get_player_summaries,
    vanity_url,
)
import requests

app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

@app.route('/')
def index():
    """
    render the steam id lookup page
    :returns: rendered lookup page
    """
    return render_template('index.html')


@app.route('/health')
def health():
    """Return a lightweight health response without external API calls."""
    return jsonify(status='ok')

@app.route('/lookup', methods=['POST'])
def lookup():
    """
    fetch and render steam profile library and inventory values
    :returns: rendered results page or lookup page with an error
    """
    if not Config.STEAM_API_KEY:
        return render_template(
            'index.html',
            error="This demo is temporarily unavailable because Steam API access is not configured.",
        ), 503

    steamid_entry = request.form.get('steam_id', '').strip()
    if not steamid_entry:
        return render_template('index.html', error="Please provide a valid SteamID")

    if steamid_entry.isdigit():
        if len(steamid_entry) != 17:
            return render_template('index.html', error="A SteamID must contain exactly 17 digits.")
    elif len(steamid_entry) > 64:
        return render_template('index.html', error="The vanity name is too long.")

    try:
        # vanity names
        if not steamid_entry.isdigit():
            steam_id = vanity_url(steamid_entry)
        else:
            steam_id = steamid_entry

        user_data = get_owned_games(steam_id)
        if not isinstance(user_data.get('response'), dict):
            raise ValueError("Steam library data is unavailable. Confirm that the profile and game details are public.")

        # player info
        player_data = get_player_summaries(steam_id)
        if 'players' in player_data.get('response', {}) and player_data['response']['players']:
            player = player_data['response']['players'][0]
            user_data['player'] = {
                'steamid': player.get('steamid'),
                'name': player.get('personaname'),
                'profile_url': player.get('profileurl'),
                'avatar': player.get('avatar'),
                'avatar_medium': player.get('avatarmedium'),
                'avatar_full': player.get('avatarfull')
            }
        else:
            raise ValueError("Steam profile data is unavailable. Confirm that the profile is public.")

        # Steam omits "games" for an empty public library. Normalize that
        # response so the results page can still render zero-value statistics.
        if 'response' in user_data:
            games = user_data['response'].get('games', [])
            app_ids = [game['appid'] for game in games]
            achievement_app_ids = [
                game['appid']
                for game in games
                if game.get('playtime_forever', 0) > 0
            ]

            # total value
            with ThreadPoolExecutor(max_workers=3) as executor:
                price_future = executor.submit(get_game_value_parallel, app_ids)
                achievement_future = executor.submit(
                    get_achievement_summaries,
                    steam_id,
                    achievement_app_ids,
                )
                inventory_future = executor.submit(get_inventory_values, steam_id, app_ids)
                prices = price_future.result()
                achievements = achievement_future.result()
                inventories = inventory_future.result()
            total = 0.0
            priced_games = 0
            for game in games:
                app_id = game['appid']
                game['value'] = prices.get(app_id)
                game['achievements'] = achievements.get(app_id, {'status': 'not_checked'})
                game['inventory'] = inventories.get(app_id)
                game['inventory_supported'] = app_id in inventories
                if game['value'] is not None:
                    total += game['value']
                    priced_games += 1

            # sort games by playtime in descending order
            sorted_games = sorted(games, key=lambda game: game.get('playtime_forever', 0), reverse=True)


            # calculate stats
            total_games = len(games)
            total_playtime_minutes = sum(game.get('playtime_forever', 0) for game in games)
            total_playtime_hours = round(total_playtime_minutes / 60, 2)
            average_playtime_hours = round(total_playtime_hours / total_games, 2) if total_games > 0 else 0
            total_value = round(total, 2) if priced_games else None
            achievement_summaries = [
                summary
                for summary in achievements.values()
                if summary.get('status') == 'ok'
            ]
            total_achievements = sum(summary['unlocked'] for summary in achievement_summaries)
            total_available_achievements = sum(summary['total'] for summary in achievement_summaries)
            achievement_statuses = [
                summary.get('status', 'api_unavailable')
                for summary in achievements.values()
                if summary.get('status') != 'ok'
            ]
            achievement_status = 'ok'
            if not achievement_summaries:
                achievement_status = next(
                    (
                        status
                        for status in (
                            'rate_limited', 'timeout', 'private',
                            'api_unavailable', 'unavailable'
                        )
                        if status in achievement_statuses
                    ),
                    'unavailable',
                )
            inventory_summaries = [
                summary
                for summary in inventories.values()
                if summary is not None and summary['value'] is not None
            ]
            total_inventory_value = (
                round(sum(summary['value'] for summary in inventory_summaries), 2)
                if inventory_summaries
                else None
            )
            inventory_value_is_partial = any(
                summary.get('partial', False) or summary.get('status') != 'ok'
                for summary in inventories.values()
            )
            inventory_statuses = [
                summary.get('status', 'api_unavailable')
                for summary in inventories.values()
            ]
            inventory_status = 'ok'
            if total_inventory_value is None:
                if not Config.STEAMWEBAPI_KEY:
                    inventory_status = 'not_configured'
                elif not inventories:
                    inventory_status = 'no_supported_games'
                else:
                    inventory_status = next(
                        (
                            status
                            for status in (
                                'auth_error', 'quota_exhausted', 'rate_limited',
                                'timeout', 'private', 'prices_unavailable',
                                'api_unavailable'
                            )
                            if status in inventory_statuses
                        ),
                        'api_unavailable',
                    )

            # add calculated statistics to user_data
            user_data['statistics'] = {
                'total_games': total_games,
                'total_playtime_hours': total_playtime_hours,
                'average_playtime_hours': average_playtime_hours,
                'total_value': total_value,
                'game_value_is_partial': priced_games < total_games,
                'total_achievements': total_achievements,
                'total_available_achievements': total_available_achievements,
                'achievement_data_available': bool(achievement_summaries),
                'achievement_data_is_partial': bool(
                    achievement_summaries
                    and (achievement_statuses or len(achievement_app_ids) < len(app_ids))
                ),
                'achievement_status': achievement_status,
                'total_inventory_value': total_inventory_value,
                'inventory_value_is_partial': inventory_value_is_partial,
                'inventory_api_configured': bool(Config.STEAMWEBAPI_KEY),
                'inventory_status': inventory_status,
            }
            user_data['response']['games'] = sorted_games
        return render_template('results.html', user_data=user_data)
    except ValueError as e:
        return render_template('index.html', error=str(e))
    except requests.exceptions.RequestException:
        return render_template(
            'index.html',
            error="Steam is temporarily unavailable. Please try again in a moment.",
        ), 502


if __name__ == "__main__":
    app.run(debug=True)
