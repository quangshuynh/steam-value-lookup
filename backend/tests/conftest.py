import pytest

import steam_api


@pytest.fixture(autouse=True)
def isolate_external_requests(monkeypatch):
    """Fail every test that accidentally attempts a live HTTP request."""
    steam_api.GAME_PRICE_CACHE.clear()

    def reject_network(*args, **kwargs):
        raise AssertionError("Tests must mock external HTTP requests")

    monkeypatch.setattr(steam_api.requests, "get", reject_network)
