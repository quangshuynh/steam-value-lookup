import unittest
from unittest.mock import Mock, patch

import steam_api


class SteamApiTests(unittest.TestCase):
    """
    verify steam api value lookup behavior
    :returns: steam api test case
    """
    def setUp(self):
        """
        clear cached game prices before each test
        :returns: none
        """
        steam_api.GAME_PRICE_CACHE.clear()

    @patch("steam_api.time.sleep")
    @patch("steam_api.requests.get")
    def test_store_price_retries_rate_limit(self, get, sleep):
        """
        verify store pricing retries a rate limited request
        :param get: mocked requests get function
        :param sleep: mocked sleep function
        :returns: none
        """
        limited = Mock(status_code=429, headers={"Retry-After": "0"})
        success = Mock(status_code=200, headers={})
        success.raise_for_status.return_value = None
        success.json.return_value = {
            "10": {"success": True, "data": {"price_overview": {"final": 1299}}}
        }
        get.side_effect = [limited, success]

        self.assertEqual(steam_api.get_game_value_parallel([10]), {10: 12.99})
        self.assertEqual(get.call_count, 2)

    def test_inventory_response_and_currency_parsing(self):
        """
        verify nested inventory extraction and currency parsing
        :returns: none
        """
        payload = {"data": {"items": [{"pricelatestsell": "$1,234.56"}]}}

        self.assertEqual(steam_api._inventory_items(payload), payload["data"]["items"])
        self.assertEqual(steam_api._parse_currency("$1,234.56"), 1234.56)
        self.assertEqual(steam_api._parse_currency("0,42 EUR"), 0.42)

    @patch("steam_api.requests.get")
    def test_store_prices_request_each_game(self, get):
        """
        verify store prices request each game separately
        :param get: mocked requests get function
        :returns: none
        """
        response = Mock(status_code=200, headers={})
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "10": {"success": True, "data": {"price_overview": {"final": 999}}},
            "20": {"success": True, "data": {"is_free": True}},
        }
        get.return_value = response

        result = steam_api.get_game_value_parallel([10, 20])

        self.assertEqual(result, {10: 9.99, 20: 0.0})
        self.assertEqual(get.call_count, 2)
        requested_app_ids = {
            call.kwargs["params"]["appids"]
            for call in get.call_args_list
        }
        self.assertEqual(requested_app_ids, {"10", "20"})

    @patch.object(steam_api.Config, "STEAMWEBAPI_KEY", "inventory-key")
    @patch("steam_api.requests.get")
    def test_inventory_requests_parsed_prices_with_query_key(self, get):
        """
        verify inventory requests use parsed prices and query authentication
        :param get: mocked requests get function
        :returns: none
        """
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [{"count": 2, "pricelatest": 1.25}]
        }
        get.return_value = response

        result = steam_api.get_inventory_values("76561198000000000", [730])

        self.assertEqual(result[730]["value"], 2.5)
        request = get.call_args.kwargs
        self.assertEqual(request["params"]["key"], "inventory-key")
        self.assertEqual(request["params"]["parse"], 1)
        self.assertEqual(request["params"]["currency"], "USD")
        self.assertEqual(request["timeout"], 12)

    @patch("steam_api.get_player_achievements")
    def test_achievement_rate_limit_status(self, get_achievements):
        """
        verify achievement rate limits are preserved in the result
        :param get_achievements: mocked achievement request function
        :returns: none
        """
        response = Mock(status_code=429)
        get_achievements.side_effect = steam_api.requests.HTTPError(response=response)

        result = steam_api.get_achievement_summaries("76561198000000000", [10])

        self.assertEqual(result[10]["status"], "rate_limited")

    def test_inventory_http_status_classification(self):
        """
        verify inventory errors distinguish authentication and quota failures
        :returns: none
        """
        auth_response = Mock()
        auth_response.json.return_value = {"error": "invalid api key"}
        quota_response = Mock()
        quota_response.json.return_value = {"error": "credits exhausted"}

        self.assertEqual(steam_api._inventory_http_status(auth_response), "auth_error")
        self.assertEqual(steam_api._inventory_http_status(quota_response), "quota_exhausted")

    @patch("steam_api.requests.get")
    def test_vanity_url_returns_resolved_steam_id(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "response": {"success": 1, "steamid": "76561198000000000"}
        }
        get.return_value = response

        result = steam_api.vanity_url("test-player")

        self.assertEqual(result, "76561198000000000")
        self.assertEqual(get.call_args.kwargs["params"]["vanityurl"], "test-player")

    @patch("steam_api.requests.get")
    def test_vanity_url_rejects_unknown_name(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": {"success": 42}}
        get.return_value = response

        with self.assertRaisesRegex(ValueError, "Could not resolve vanity URL"):
            steam_api.vanity_url("missing-user")

    @patch("steam_api.time.sleep")
    @patch("steam_api.requests.get")
    def test_store_price_returns_none_for_unavailable_and_malformed_data(self, get, sleep):
        response = Mock(status_code=200, headers={})
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "10": {"success": False},
            "20": {"success": True, "data": {"price_overview": {"final": "unknown"}}},
        }
        get.return_value = response

        result = steam_api.get_game_value_parallel([10, 20])

        self.assertEqual(result, {10: None, 20: None})

    @patch("steam_api.get_player_achievements")
    def test_achievement_summary_counts_unlocked_items(self, get_achievements):
        get_achievements.return_value = {
            "playerstats": {
                "success": True,
                "achievements": [{"achieved": 1}, {"achieved": 0}, {"achieved": 1}],
            }
        }

        result = steam_api.get_achievement_summaries("76561198000000000", [10])

        self.assertEqual(result[10], {"status": "ok", "unlocked": 2, "total": 3})

    @patch("steam_api.get_player_achievements")
    def test_achievement_summary_handles_unavailable_data(self, get_achievements):
        get_achievements.return_value = {"playerstats": {"success": False}}

        result = steam_api.get_achievement_summaries("76561198000000000", [10])

        self.assertEqual(result[10], {"status": "unavailable"})


if __name__ == "__main__":
    unittest.main()
