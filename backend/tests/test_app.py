from unittest.mock import patch

import pytest

from config import Config

# app.py initializes its database at import time; point that initialization at
# memory so route tests never touch the developer's instance database.
Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module.Config, "STEAM_API_KEY", "test-key")
    app_module.app.config.update(
        TESTING=True,
    )
    return app_module.app.test_client()


def profile_payload():
    return {
        "response": {
            "players": [{
                "steamid": "76561198000000000",
                "personaname": "Test Player",
                "profileurl": "https://steamcommunity.com/id/test-player/",
                "avatar": "avatar.jpg",
                "avatarmedium": "avatar-medium.jpg",
                "avatarfull": "avatar-full.jpg",
            }]
        }
    }


def test_index_renders_search_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'id="steam_id"' in response.data
    assert b"Vanity URL" in response.data


def test_health_check_is_local_and_successful(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@patch.object(app_module.Config, "STEAM_API_KEY", None)
def test_lookup_reports_missing_server_api_configuration(client):
    response = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert response.status_code == 503
    assert b"Steam API access is not configured" in response.data


@patch.object(app_module.Config, "STEAM_API_KEY", "test-key")
def test_lookup_rejects_invalid_numeric_steam_id(client):
    response = client.post("/lookup", data={"steam_id": "12345"})

    assert response.status_code == 200
    assert b"exactly 17 digits" in response.data


def test_lookup_rejects_missing_input(client):
    response = client.post("/lookup", data={})

    assert response.status_code == 200
    assert b"Please provide a valid SteamID" in response.data


@patch.object(app_module.Config, "STEAM_API_KEY", "test-key")
def test_lookup_rejects_excessive_vanity_name(client):
    response = client.post("/lookup", data={"steam_id": "a" * 65})

    assert response.status_code == 200
    assert b"vanity name is too long" in response.data


@patch.object(app_module, "get_owned_games", side_effect=app_module.requests.ConnectionError())
def test_lookup_handles_upstream_network_failure(owned_games, client):
    response = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert response.status_code == 502
    assert b"Steam is temporarily unavailable" in response.data


@patch.object(app_module, "get_owned_games")
def test_lookup_handles_rejected_steam_api_key_without_exposing_details(owned_games, client):
    response = app_module.requests.Response()
    response.status_code = 403
    owned_games.side_effect = app_module.requests.HTTPError(
        "upstream detail must not be rendered",
        response=response,
    )

    result = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert result.status_code == 502
    assert b"Steam is temporarily unavailable" in result.data
    assert b"upstream detail" not in result.data


@patch.object(app_module, "get_inventory_values", return_value={})
@patch.object(app_module, "get_achievement_summaries", return_value={})
@patch.object(app_module, "get_game_value_parallel", return_value={10: 12.99, 20: 0.0})
@patch.object(app_module, "get_player_summaries", side_effect=lambda steam_id: profile_payload())
@patch.object(app_module, "get_owned_games", return_value={
    "response": {
        "games": [
            {"appid": 10, "name": "Paid Game", "playtime_forever": 120},
            {"appid": 20, "name": "Free Game", "playtime_forever": 0},
        ]
    }
})
def test_lookup_renders_profile_games_and_aggregate_value(
    owned_games, player, prices, achievements, inventories, client
):
    response = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert response.status_code == 200
    assert b"Test Player" in response.data
    assert b"Paid Game" in response.data
    assert b"$12.99" in response.data
    prices.assert_called_once_with([10, 20])
    achievements.assert_called_once_with("76561198000000000", [10])


@patch.object(app_module, "get_inventory_values", return_value={})
@patch.object(app_module, "get_achievement_summaries", return_value={})
@patch.object(app_module, "get_game_value_parallel", return_value={})
@patch.object(app_module, "get_player_summaries", side_effect=lambda steam_id: profile_payload())
@patch.object(app_module, "get_owned_games", return_value={"response": {}})
def test_lookup_handles_library_with_no_games(
    owned_games, player, prices, achievements, inventories, client
):
    response = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert response.status_code == 200
    assert b"Test Player" in response.data
    assert b'id="total-games">0<' in response.data
    assert b'id="total-hours">0.0<' in response.data


@patch.object(app_module, "vanity_url", side_effect=ValueError("Unknown vanity name"))
def test_lookup_shows_vanity_resolution_error(vanity, client):
    response = client.post("/lookup", data={"steam_id": "missing-user"})

    assert response.status_code == 200
    assert b"Unknown vanity name" in response.data


@patch.object(app_module, "get_inventory_values", return_value={})
@patch.object(app_module, "get_achievement_summaries", return_value={})
@patch.object(app_module, "get_game_value_parallel", return_value={})
@patch.object(app_module, "get_owned_games", return_value={"response": {}})
@patch.object(app_module, "get_player_summaries", side_effect=lambda steam_id: profile_payload())
@patch.object(app_module, "vanity_url", return_value="76561198000000000")
def test_lookup_resolves_vanity_before_fetching_profile(
    vanity, player, owned_games, prices, achievements, inventories, client
):
    response = client.post("/lookup", data={"steam_id": "test-player"})

    assert response.status_code == 200
    vanity.assert_called_once_with("test-player")
    owned_games.assert_called_once_with("76561198000000000")


@patch.object(app_module, "get_inventory_values", return_value={})
@patch.object(app_module, "get_achievement_summaries", return_value={})
@patch.object(app_module, "get_game_value_parallel", return_value={})
@patch.object(app_module, "get_owned_games", return_value={"response": {}})
@patch.object(app_module, "get_player_summaries", side_effect=lambda steam_id: profile_payload())
@patch.object(app_module, "vanity_url")
def test_lookup_uses_numeric_steam_id_without_vanity_resolution(
    vanity, player, owned_games, prices, achievements, inventories, client
):
    response = client.post("/lookup", data={"steam_id": "76561198000000000"})

    assert response.status_code == 200
    vanity.assert_not_called()
    owned_games.assert_called_once_with("76561198000000000")
