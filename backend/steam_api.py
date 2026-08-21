import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import Config


logger = logging.getLogger(__name__)
INVENTORY_CONTEXTS = {
    440: 2,      # Team Fortress 2
    570: 2,      # Dota 2
    730: 2,      # Counter-Strike 2
    252490: 2,   # Rust
}
MAX_MARKET_ITEMS_PER_GAME = 40
MARKET_PRICE_CACHE = {}
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


def _parse_usd_price(value):
    if not value:
        return None
    numeric_value = re.sub(r"[^0-9.]", "", value)
    try:
        return float(numeric_value)
    except ValueError:
        return None


def _get_market_price(app_id, market_hash_name):
    cache_key = (app_id, market_hash_name)
    if cache_key in MARKET_PRICE_CACHE:
        return MARKET_PRICE_CACHE[cache_key]

    try:
        response = requests.get(
            "https://steamcommunity.com/market/priceoverview/",
            params={
                "appid": app_id,
                "currency": 1,
                "market_hash_name": market_hash_name,
            },
            headers={**STEAM_HEADERS, "Referer": "https://steamcommunity.com/market/"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        price = _parse_usd_price(data.get("lowest_price") or data.get("median_price"))
        if price is not None:
            MARKET_PRICE_CACHE[cache_key] = price
        return price
    except (requests.RequestException, AttributeError, TypeError, ValueError):
        return None


def get_inventory(steam_id, app_id, context_id=2):
    url = f"https://steamcommunity.com/inventory/{steam_id}/{app_id}/{context_id}"
    assets = []
    descriptions = {}
    start_asset_id = None

    while True:
        params = {"l": "english", "count": 2000}
        if start_asset_id:
            params["start_assetid"] = start_asset_id

        response = requests.get(
            url,
            params=params,
            headers={**STEAM_HEADERS, "Referer": "https://steamcommunity.com/inventory/"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            return None

        assets.extend(data.get("assets", []))
        for description in data.get("descriptions", []):
            key = (description.get("classid"), description.get("instanceid", "0"))
            descriptions[key] = description

        if not data.get("more_items"):
            break
        start_asset_id = data.get("last_assetid")
        if not start_asset_id:
            break

    return {"assets": assets, "descriptions": descriptions}


def get_inventory_values(steam_id, app_ids):
    owned_app_ids = set(app_ids)
    summaries = {}

    for app_id, context_id in INVENTORY_CONTEXTS.items():
        if app_id not in owned_app_ids:
            continue

        try:
            inventory = get_inventory(steam_id, app_id, context_id)
        except (requests.RequestException, AttributeError, TypeError, ValueError) as error:
            logger.info("Inventory unavailable for app %s: %s", app_id, error)
            summaries[app_id] = {
                "status": "private_or_unavailable",
                "value": None,
                "partial": False,
            }
            continue

        if inventory is None:
            summaries[app_id] = {
                "status": "private_or_unavailable",
                "value": None,
                "partial": False,
            }
            continue

        market_items = {}
        marketable_item_count = 0
        for asset in inventory["assets"]:
            key = (asset.get("classid"), asset.get("instanceid", "0"))
            description = inventory["descriptions"].get(key, {})
            if description.get("marketable") != 1 or not description.get("market_hash_name"):
                continue

            quantity = int(asset.get("amount", 1))
            marketable_item_count += quantity
            market_hash_name = description["market_hash_name"]
            market_items[market_hash_name] = market_items.get(market_hash_name, 0) + quantity

        total_value = 0.0
        priced_types = 0
        items_to_price = list(market_items.items())[:MAX_MARKET_ITEMS_PER_GAME]
        for index, (market_hash_name, quantity) in enumerate(items_to_price):
            price = _get_market_price(app_id, market_hash_name)
            if price is not None:
                total_value += price * quantity
                priced_types += 1
            if index + 1 < len(items_to_price):
                time.sleep(1)

        summaries[app_id] = {
            "status": "ok" if not market_items or priced_types else "prices_unavailable",
            "item_count": sum(int(asset.get("amount", 1)) for asset in inventory["assets"]),
            "marketable_item_count": marketable_item_count,
            "value": (
                round(total_value, 2)
                if priced_types
                else 0.0 if not market_items else None
            ),
            "priced_types": priced_types,
            "total_market_types": len(market_items),
            "partial": priced_types < len(market_items),
        }

    return summaries
