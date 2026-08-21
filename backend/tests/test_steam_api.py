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


if __name__ == "__main__":
    unittest.main()

