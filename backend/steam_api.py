import requests
from config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed



def get_owned_games(steam_id):
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": Config.STEAM_API_KEY,   # steam api key
        "steamid": steam_id,
        "include_appinfo": True,
        "include_played_free_games": True,
        "format": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_player_summaries(steam_id):
    url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
    params = {
        "key": Config.STEAM_API_KEY,
        "steamids": steam_id,
        "format": "json",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def vanity_url(vanity_url):
    url = "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
    params = {
        "key": Config.STEAM_API_KEY,
        "vanityurl": vanity_url,
        "format": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if data['response']['success'] == 1:
        return data['response']['steamid']
    else:
        raise ValueError("Could not resolve vanity URL. Please provide a valid SteamID or vanity name.")
    

def get_player_achievements(steam_id, app_id):
    url = "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
    params = {
        "key": Config.STEAM_API_KEY,
        "steamid": steam_id,
        "appid": app_id
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_user_game_stats(steam_id, app_id):
    url = " http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"
    params = {
        "key": Config.STEAM_API_KEY,
        "steamid": steam_id,
        "appid": app_id
    }
    response=requests.get(url, params)
    response.raise_for_status()
    return response.json()
    

def get_game_value_parallel(app_ids):
    url = "https://store.steampowered.com/api/appdetails"
    results = {}

    # helper function to fetch the price for a single app ID
    def fetch_price(app_id):
        params = {"appids": app_id}
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data[str(app_id)]['success']:
                game_data = data[str(app_id)]['data']
                if 'price_overview' in game_data:
                    return app_id, float(game_data['price_overview']['final_formatted'].replace('$', '').replace(',', ''))
                else:
                    return app_id, 0.0
            else:
                return app_id, 0.0
        except Exception:
            return app_id, 0.0

    # use ThreadPoolExecutor to fetch prices concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_price, app_id) for app_id in app_ids]
        for future in as_completed(futures):
            app_id, price = future.result()
            results[app_id] = price
    return results


def get_inventory(steam_id, app_id):
    url = f"https://steamcommunity.com/id/{steam_id}/inventory#{app_id}"
    response = requests.get(url)
    return response.json()
