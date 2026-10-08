# src/services/imdb_service.py
# Network ingestion and IMDb user-ID handling.
# All business logic here is Streamlit-free and fully testable.

import re

import requests
from bs4 import BeautifulSoup

from src.utils.constants import IMDB_EXPORT_URL, IMDB_USER_PAGE_URL


# ---------------------------------------------------------------------------
# Custom domain exceptions
# ---------------------------------------------------------------------------


class UserListPrivateError(Exception):
    """Raised when the IMDb user's ratings list is private (HTTP 403)."""


class IMDbConnectionError(Exception):
    """Raised when the IMDb endpoint is unreachable or returns a non-200/non-403 status."""


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


# IMDb user IDs may be numeric (ur12345678) or alphanumeric/dotted
# (e.g. p.xd2gqvhctziu3txmdxu7dzktoi). The common invariant is that they
# appear as the path segment immediately after /user/ in an IMDb URL.
_IMDB_USER_ID_RE = re.compile(r"[A-Za-z0-9][\w.]*")


def extract_user_id(raw_input: str) -> str | None:
    """
    Extracts and normalises an IMDb user identifier.

    Accepts:
    - A full IMDb profile URL: the ID is the path segment after /user/
      e.g. https://www.imdb.com/user/p.xd2gqvhctziu3txmdxu7dzktoi?ref_=...
    - A bare numeric ID:  "ur12345678"
    - A bare alphanumeric/dotted ID: "p.xd2gqvhctziu3txmdxu7dzktoi"
    - Whitespace-padded variants of the above.

    Returns the extracted ID string, or None if nothing recognisable is found.
    """
    if not raw_input:
        return None

    stripped = raw_input.strip()

    # Priority 1: extract the segment immediately after /user/ in a URL.
    url_match = re.search(r"/user/([A-Za-z0-9][\w.]*)", stripped)
    if url_match:
        return url_match.group(1)

    # Priority 2: accept a bare ID — must start with a letter (IMDb IDs always do).
    if re.fullmatch(r"[A-Za-z][\w.]*", stripped):
        return stripped

    return None


def fetch_ratings_by_user_id(
    user_id: str, timeout: int = 10, session_cookie: str | None = None
) -> str:
    """
    Fetches the CSV export for the given IMDb user ID.

    Strategy:
    1. Load the user's public ratings HTML page (authenticated if session_cookie given).
    2. Parse it with BeautifulSoup to locate the canonical CSV download <a> tag.
    3. If a resolved URL is found, fetch from that URL; otherwise fall back to
       the template export URL.

    Args:
        user_id:        Extracted IMDb user ID string.
        timeout:        HTTP request timeout in seconds.
        session_cookie: Value of the IMDb `at-main` session cookie. When provided,
                        it is sent with every request so IMDb treats the call as
                        an authenticated session.

    Returns the raw CSV text payload on HTTP 200.

    Raises:
        UserListPrivateError  — when IMDb returns HTML instead of CSV (login required).
        IMDbConnectionError   — on any other non-200 response or connection failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    cookies = {}
    if session_cookie:
        cookies["at-main"] = session_cookie.strip()

    export_url = IMDB_EXPORT_URL.format(user_id=user_id)

    # --- Step 1: Attempt to resolve the canonical CSV URL via BS4 ---
    try:
        page_url = IMDB_USER_PAGE_URL.format(user_id=user_id)
        page_response = requests.get(
            page_url, timeout=timeout, headers=headers, cookies=cookies
        )
        if page_response.status_code == 200:
            soup = BeautifulSoup(page_response.text, "html.parser")
            # Look for an <a> tag whose href contains "/ratings/export" or ends with .csv
            csv_link = soup.find(
                "a",
                href=re.compile(r"/ratings/export|\.csv", re.IGNORECASE),
            )
            if csv_link and csv_link.get("href"):
                href = csv_link["href"]
                # Resolve relative URLs.
                if href.startswith("http"):
                    export_url = href
                else:
                    export_url = f"https://www.imdb.com{href}"
    except requests.exceptions.RequestException:
        # Page fetch failed; fall back to the template URL silently.
        pass

    # --- Step 2: Fetch the CSV ---
    try:
        response = requests.get(
            export_url, timeout=timeout, headers=headers, cookies=cookies
        )
    except requests.exceptions.Timeout as exc:
        raise IMDbConnectionError(
            f"Request to IMDb timed out after {timeout}s."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise IMDbConnectionError(f"Failed to connect to IMDb: {exc}") from exc

    if response.status_code == 403:
        raise UserListPrivateError(
            "This IMDb user's ratings list is private. "
            "Ask them to make it public before importing."
        )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        raise IMDbConnectionError(
            f"IMDb returned an unexpected status ({response.status_code})."
        ) from exc

    # Guard: if IMDb returned HTML instead of CSV (e.g. a login redirect),
    # the content-type will not be text/csv and the body will start with "<".
    content_type = response.headers.get("Content-Type", "")
    body_start = response.text.lstrip()[:1]
    if body_start == "<" or ("text/html" in content_type and "text/csv" not in content_type):
        raise UserListPrivateError(
            "IMDb returned a web page instead of a CSV file — your session cookie may be "
            "missing, expired, or incorrect. Please follow the login steps in the sidebar."
        )

    return response.text
