import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import Config


logger = logging.getLogger(__name__)
STEAMWEBAPI_GAMES = {
    440: "tf2",
    570: "dota",
    730: "cs2",
    252490: "rust",
    578080: "pubg",
    590830: "sbox",
}
GAME_PRICE_CACHE = {}
STEAM_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


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
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_achievement_summaries(steam_id, app_ids):
    def fetch_summary(app_id):
        try:
            data = get_player_achievements(steam_id, app_id)
            player_stats = data.get("playerstats", {})
            if not player_stats.get("success", False):
                return app_id, None

            achievements = player_stats.get("achievements", [])
            return app_id, {
                "unlocked": sum(item.get("achieved", 0) == 1 for item in achievements),
                "total": len(achievements),
            }
        except (requests.RequestException, AttributeError, TypeError, ValueError):
            # Many games have no achievements, and private profiles return an error.
            return app_id, None

    summaries = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_summary, app_id) for app_id in app_ids]
        for future in as_completed(futures):
            app_id, summary = future.result()
            summaries[app_id] = summary
    return summaries


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
    results = {
        app_id: GAME_PRICE_CACHE[app_id]
        for app_id in app_ids
        if app_id in GAME_PRICE_CACHE
    }

    def fetch_price(app_id):
        params = {
            "appids": app_id,
            "cc": "us",
            "l": "en",
        }
        try:
            response = requests.get(
                url,
                params=params,
                headers=STEAM_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json().get(str(app_id), {})
            if not payload.get("success"):
                return app_id, None

            game_data = payload.get("data", {})
            if game_data.get("is_free"):
                return app_id, 0.0

            final_price = game_data.get("price_overview", {}).get("final")
            if isinstance(final_price, int):
                return app_id, final_price / 100
            return app_id, None
        except (requests.RequestException, AttributeError, TypeError, ValueError) as error:
            logger.info("Store price unavailable for app %s: %s", app_id, error)
            return app_id, None

    missing_app_ids = [app_id for app_id in app_ids if app_id not in results]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch_price, app_id) for app_id in missing_app_ids]
        for future in as_completed(futures):
            app_id, price = future.result()
            results[app_id] = price
            if price is not None:
                GAME_PRICE_CACHE[app_id] = price
    return results


def get_inventory_values(steam_id, app_ids):
    owned_app_ids = set(app_ids)
    supported_games = [
        (app_id, game)
        for app_id, game in STEAMWEBAPI_GAMES.items()
        if app_id in owned_app_ids
    ]
    if not Config.STEAMWEBAPI_KEY:
        return {
            app_id: {"status": "not_configured", "value": None, "partial": False}
            for app_id, _ in supported_games
        }

    def fetch_inventory(app_id, game):
        try:
            response = requests.get(
                "https://www.steamwebapi.com/steam/api/inventory",
                params={
                    "steam_id": steam_id,
                    "game": game,
                    "with_prices": 1,
                    "group": 1,
                    "currency": "USD",
                    "production": 1,
                    "limit": 10000,
                },
                headers={"X-API-Key": Config.STEAMWEBAPI_KEY, **STEAM_HEADERS},
                timeout=30,
            )
            if response.status_code == 403:
                return app_id, {"status": "private", "value": None, "partial": False}
            if response.status_code in (410, 411):
                return app_id, {"status": "ok", "value": 0.0, "partial": False, "item_count": 0}
            response.raise_for_status()

            data = response.json()
            if isinstance(data, dict):
                items = data.get("data") or data.get("items") or data.get("inventory") or []
            else:
                items = data
            if not isinstance(items, list):
                raise ValueError("Unexpected SteamWebAPI inventory response")

            total_value = 0.0
            item_count = 0
            unpriced_items = 0
            for item in items:
                quantity = int(item.get("count") or item.get("amount") or 1)
                item_count += quantity
                price = next(
                    (
                        item.get(field)
                        for field in ("pricelatest", "pricesafe", "pricemix", "pricereal")
                        if item.get(field) is not None
                    ),
                    None,
                )
                if isinstance(price, str):
                    price = re.sub(r"[^0-9.]", "", price)
                try:
                    total_value += float(price) * quantity
                except (TypeError, ValueError):
                    unpriced_items += quantity

            return app_id, {
                "status": "ok" if not unpriced_items else "prices_unavailable",
                "value": round(total_value, 2) if item_count > unpriced_items else None,
                "partial": unpriced_items > 0,
                "item_count": item_count,
            }
        except (requests.RequestException, AttributeError, TypeError, ValueError) as error:
            logger.info("SteamWebAPI inventory unavailable for app %s: %s", app_id, error)
            return app_id, {"status": "api_unavailable", "value": None, "partial": False}

    summaries = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch_inventory, app_id, game) for app_id, game in supported_games]
        for future in as_completed(futures):
            app_id, summary = future.result()
            summaries[app_id] = summary
    return summaries
