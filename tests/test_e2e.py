# tests/test_e2e.py
# End-to-end tests using streamlit.testing.v1.AppTest.
# Each test starts from a cold app state; no real network calls are made.

from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import SAMPLE_CSV, MISSING_COL_CSV
from src.services.imdb_service import UserListPrivateError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_app() -> AppTest:
    """Return a fresh AppTest instance targeting app.py."""
    return AppTest.from_file("app.py", default_timeout=30)


def _upload_csv(at: AppTest, csv_content: str = SAMPLE_CSV) -> AppTest:
    """Simulate a CSV file upload and run the app."""
    at.run()
    at.file_uploader[0].upload(
        name="ratings.csv",
        content=csv_content.encode("utf-8"),
        mime="text/csv",
    )
    at.run()
    return at


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


def test_e2e_csv_upload_populates_dataframe():
    """Upload a valid CSV → dataframe component renders the expected number of rows."""
    at = _upload_csv(_load_app())
    # The app renders a st.dataframe; verify it is present and non-empty.
    assert len(at.dataframe) > 0
    assert at.dataframe[0].value is not None


def test_e2e_filter_slider_reduces_rows():
    """Set rating slider to 8–10 → rendered row count decreases vs unfiltered."""
    at = _upload_csv(_load_app())
    unfiltered_rows = len(at.dataframe[0].value)

    # Move the slider to min=8, max=10.
    at.slider[0].set_value((8, 10))
    at.run()

    filtered_rows = len(at.dataframe[0].value)
    assert filtered_rows < unfiltered_rows


def test_e2e_title_search_filters_results():
    """Type a known title substring → only matching rows are displayed."""
    at = _upload_csv(_load_app())

    at.text_input[1].set_value("Shawshank")
    at.run()

    df = at.dataframe[0].value
    assert len(df) == 1
    assert "Shawshank" in df["Title"].iloc[0]


def test_e2e_analytics_tab_renders_charts():
    """Switch to Analytics tab → metric components and chart components are non-null."""
    at = _upload_csv(_load_app())

    # Switch to the Analytics tab (index 1).
    at.tabs[0].set_value("📊 Analytics Dashboard")
    at.run()

    # At least three metrics should be rendered (mean, median, total).
    assert len(at.metric) >= 3
    # At least one Altair chart (vega_lite_chart) should be present.
    assert len(at.vega_lite_chart) >= 1


def test_e2e_export_csv_button_present():
    """After upload, the Export CSV download button must be rendered."""
    at = _upload_csv(_load_app())
    labels = [btn.label for btn in at.button]
    download_labels = [btn.label for btn in at.download_button]
    assert any("CSV" in lbl for lbl in download_labels)


def test_e2e_export_excel_button_present():
    """After upload, the Export Excel download button must be rendered."""
    at = _upload_csv(_load_app())
    download_labels = [btn.label for btn in at.download_button]
    assert any("Excel" in lbl for lbl in download_labels)


def test_e2e_invalid_user_id_shows_error():
    """Entering an invalid user ID and clicking Fetch → st.error is displayed."""
    at = _load_app()
    at.run()

    at.text_input[0].set_value("invalid123")
    at.button[0].click()
    at.run()

    assert len(at.error) > 0


def test_e2e_private_list_shows_error():
    """When fetch raises UserListPrivateError → st.error is shown in the UI."""
    at = _load_app()
    at.run()

    with patch(
        "src.services.imdb_service.fetch_ratings_by_user_id",
        side_effect=UserListPrivateError("List is private"),
    ):
        at.text_input[0].set_value("ur12345678")
        at.button[0].click()
        at.run()

    assert len(at.error) > 0


def test_e2e_missing_columns_shows_toast():
    """Uploading a CSV missing required columns → st.toast error is displayed."""
    at = _load_app()
    at.run()

    at.file_uploader[0].upload(
        name="bad_ratings.csv",
        content=MISSING_COL_CSV.encode("utf-8"),
        mime="text/csv",
    )
    at.run()

    # st.toast surfaces as a toast component in AppTest.
    assert len(at.toast) > 0
    assert any("❌" in t.body or "missing" in t.body.lower() for t in at.toast)
