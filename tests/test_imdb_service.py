# tests/test_imdb_service.py
# Unit tests for extract_user_id (pure logic) and
# integration tests for fetch_ratings_by_user_id (mocked HTTP).

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.services.imdb_service import (
    IMDbConnectionError,
    UserListPrivateError,
    extract_user_id,
    fetch_ratings_by_user_id,
)

# ---------------------------------------------------------------------------
# extract_user_id — pure unit tests
# ---------------------------------------------------------------------------


def test_extract_user_id_valid_bare_numeric():
    assert extract_user_id("ur12345678") == "ur12345678"


def test_extract_user_id_valid_bare_alphanumeric():
    # Real-world dotted alphanumeric IMDb ID.
    assert extract_user_id("p.xd2gqvhctziu3txmdxu7dzktoi") == "p.xd2gqvhctziu3txmdxu7dzktoi"


def test_extract_user_id_valid_url_numeric():
    url = "https://www.imdb.com/user/ur12345678/ratings"
    assert extract_user_id(url) == "ur12345678"


def test_extract_user_id_valid_url_alphanumeric():
    url = "https://www.imdb.com/user/p.xd2gqvhctziu3txmdxu7dzktoi?ref_=hm_nv_profile"
    assert extract_user_id(url) == "p.xd2gqvhctziu3txmdxu7dzktoi"


def test_extract_user_id_valid_long_url():
    url = "https://www.imdb.com/user/ur987654321/ratings?sort=your_rating"
    assert extract_user_id(url) == "ur987654321"


def test_extract_user_id_invalid_no_prefix():
    # Plain digits with no letters are not a valid IMDb ID.
    assert extract_user_id("12345678") is None


def test_extract_user_id_invalid_letters_in_digits():
    # ur123abc is now valid — it is an alphanumeric bare ID.
    assert extract_user_id("ur123abc") == "ur123abc"


def test_extract_user_id_empty_string():
    assert extract_user_id("") is None


def test_extract_user_id_whitespace_only():
    assert extract_user_id("   ") is None


def test_extract_user_id_whitespace_stripped():
    assert extract_user_id("  ur99  ") == "ur99"


def test_extract_user_id_many_digits():
    assert extract_user_id("ur000000001") == "ur000000001"


def test_extract_user_id_single_digit():
    assert extract_user_id("ur1") == "ur1"


# ---------------------------------------------------------------------------
# fetch_ratings_by_user_id — integration tests (mocked HTTP)
# ---------------------------------------------------------------------------

FAKE_CSV = "Const,Your Rating,Title\ntt0000001,8,Test Movie\n"
FAKE_HTML_WITH_LINK = (
    '<html><body>'
    '<a href="https://www.imdb.com/user/ur123/ratings/export">Export</a>'
    '</body></html>'
)
FAKE_HTML_NO_LINK = "<html><body><p>No export link here.</p></body></html>"


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    """Helper: create a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    if status_code >= 400:
        http_error = requests.exceptions.HTTPError(response=mock)
        mock.raise_for_status.side_effect = http_error
    else:
        mock.raise_for_status.return_value = None
    return mock


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_200_returns_csv_text(mock_get):
    """HTTP 200 on both the page and export requests → returns CSV text."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_WITH_LINK),  # page fetch
        _mock_response(200, FAKE_CSV),              # CSV fetch
    ]
    result = fetch_ratings_by_user_id("ur123")
    assert result == FAKE_CSV


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_403_raises_UserListPrivateError(mock_get):
    """403 on the CSV fetch raises UserListPrivateError."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_NO_LINK),  # page fetch (no BS4 link)
        _mock_response(403),                     # CSV fetch returns 403
    ]
    with pytest.raises(UserListPrivateError):
        fetch_ratings_by_user_id("ur123")


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_404_raises_IMDbConnectionError(mock_get):
    """404 on the CSV fetch raises IMDbConnectionError."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_NO_LINK),
        _mock_response(404),
    ]
    with pytest.raises(IMDbConnectionError):
        fetch_ratings_by_user_id("ur123")


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_500_raises_IMDbConnectionError(mock_get):
    """500 on the CSV fetch raises IMDbConnectionError."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_NO_LINK),
        _mock_response(500),
    ]
    with pytest.raises(IMDbConnectionError):
        fetch_ratings_by_user_id("ur123")


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_timeout_raises_IMDbConnectionError(mock_get):
    """requests.Timeout on the CSV fetch raises IMDbConnectionError."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_NO_LINK),
        requests.exceptions.Timeout,
    ]
    with pytest.raises(IMDbConnectionError):
        fetch_ratings_by_user_id("ur123")


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_uses_bs4_resolved_url(mock_get):
    """When the HTML page contains a CSV <a> link, that resolved URL is used."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_WITH_LINK),  # page fetch with export link
        _mock_response(200, FAKE_CSV),              # CSV fetch from resolved URL
    ]
    result = fetch_ratings_by_user_id("ur123")
    assert result == FAKE_CSV
    # Verify the second call used the BS4-resolved URL (not the template).
    second_call_url = mock_get.call_args_list[1][0][0]
    assert "ratings/export" in second_call_url


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_falls_back_when_no_bs4_link(mock_get):
    """When the HTML has no export link, falls back to the template export URL."""
    mock_get.side_effect = [
        _mock_response(200, FAKE_HTML_NO_LINK),
        _mock_response(200, FAKE_CSV),
    ]
    result = fetch_ratings_by_user_id("ur123")
    assert result == FAKE_CSV
    # Verify fallback URL contains the user ID and /ratings/export.
    second_call_url = mock_get.call_args_list[1][0][0]
    assert "ur123" in second_call_url
    assert "export" in second_call_url


@patch("src.services.imdb_service.requests.get")
def test_fetch_ratings_page_fetch_failure_falls_back(mock_get):
    """If the page fetch throws a RequestException, function gracefully falls back."""
    mock_get.side_effect = [
        requests.exceptions.ConnectionError("network error"),  # page fetch fails
        _mock_response(200, FAKE_CSV),                         # CSV fetch succeeds
    ]
    result = fetch_ratings_by_user_id("ur123")
    assert result == FAKE_CSV
