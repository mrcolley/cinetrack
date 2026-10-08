# PLAN.md — CineTrack Local

## Overview

CineTrack Local is a Python 3.13 / Streamlit local-first web application. Users import their IMDb
movie ratings (via user ID or direct CSV upload), inspect and filter the data, explore a taste-profile
analytics dashboard, and export results as CSV or Excel. All data lives in memory; nothing is written
to disk.

The plan follows the exact directory structure defined in SPEC.md §7. No additional files or folders
are introduced beyond what the spec mandates.

---

## 1. IMPLEMENTATION STEPS

Files are listed in dependency order: each file can be created after every file it imports already
exists.

---

### Step 1 — Project Scaffold & Configuration

#### 1.1 `requirements.txt`
- **Purpose:** Pin all runtime and test dependencies to the exact versions from SPEC.md §3.
- **Key contents:**
  - `streamlit==1.38.0`
  - `pandas==2.2.2`
  - `altair==5.4.1`
  - `openpyxl==3.1.5`
  - `requests==2.32.3`
  - `beautifulsoup4==4.12.3`
  - `pytest==8.3.2`
- **Dependencies:** none.

#### 1.2 `.gitignore`
- **Purpose:** Prevent `.venv/`, `__pycache__/`, `*.pyc`, and `.pytest_cache/` from being committed.
- **Dependencies:** none.

#### 1.3 `README.md`
- **Purpose:** Human-readable setup and usage guide (mirrors §6 and §10 of the spec).
- **Dependencies:** none.

---

### Step 2 — Package Init Files

#### 2.1 `src/__init__.py`
- **Purpose:** Makes `src` a Python package.
- **Key contents:** empty.

#### 2.2 `src/services/__init__.py`
- **Purpose:** Makes `src/services` a Python package.
- **Key contents:** empty.

#### 2.3 `src/utils/__init__.py`
- **Purpose:** Makes `src/utils` a Python package.
- **Key contents:** empty.

#### 2.4 `tests/__init__.py`
- **Purpose:** Makes `tests` a Python package discoverable by pytest.
- **Key contents:** empty.

---

### Step 3 — Constants

#### 3.1 `src/utils/constants.py`
- **Purpose:** Central registry of shared literals — column name mappings between raw IMDb CSV headers
  and normalised DataFrame column names, the IMDb export URL template, and the required-column list
  used by schema validation.
- **Key names:**
  - `IMDB_EXPORT_URL` — string template `"https://www.imdb.com/user/{user_id}/ratings/export"`
  - `IMDB_USER_PAGE_URL` — string template `"https://www.imdb.com/user/{user_id}/ratings"`
  - `REQUIRED_COLUMNS` — `["Const", "Your Rating", "Title"]`
  - `COLUMN_RENAME_MAP` — dict mapping raw IMDb header names (e.g. `"Your Rating"`) to normalised
    Python-friendly names (e.g. `"Your_Rating"`)
  - `ALL_COLUMNS` — ordered list of all 12 RatingRecord field names (matches SPEC.md §4)
- **Dependencies:** none.

---

### Step 4 — Service Layer

#### 4.1 `src/services/imdb_service.py`
- **Purpose:** All network I/O and IMDb identifier handling. Completely decoupled from Streamlit.
- **Key functions:**
  - `extract_user_id(raw_input: str) -> str | None`
    - Applies regex `^ur\d+$` against the stripped input (also strips full IMDb profile URLs down
      to the bare ID before matching).
    - Returns the normalised ID or `None` for any invalid input.
  - `fetch_ratings_by_user_id(user_id: str, timeout: int = 10) -> str`
    - Uses `requests.get` with the export URL from `constants.IMDB_EXPORT_URL`.
    - Before the direct export attempt, uses `requests.get` to load the user's ratings HTML page and
      passes it to `BeautifulSoup` to locate the canonical CSV download `<a>` tag; if found, uses that
      resolved URL instead.
    - Calls `response.raise_for_status()` — wraps `requests.exceptions.HTTPError` in two domain
      exceptions:
      - `UserListPrivateError` (raised on 403) — signals a private list.
      - `IMDbConnectionError` (raised on any other non-200) — generic connectivity failure.
    - Returns the raw CSV text payload on success.
  - `UserListPrivateError(Exception)` — custom exception class.
  - `IMDbConnectionError(Exception)` — custom exception class.
- **Dependencies:** `requests`, `beautifulsoup4`, `src/utils/constants.py`.

#### 4.2 `src/services/data_service.py`
- **Purpose:** CSV ingestion, DataFrame normalisation, filtering, and in-memory export. No Streamlit.
- **Key functions:**
  - `parse_imdb_csv(raw_csv_source: str | io.BytesIO | io.StringIO) -> pd.DataFrame`
    - Accepts string, `BytesIO`, or `StringIO`; wraps in `io.StringIO` if a plain string.
    - Reads with `pd.read_csv`.
    - Validates that `REQUIRED_COLUMNS` are present; raises `ValueError` with a descriptive message
      if any are missing.
    - Applies `COLUMN_RENAME_MAP` to normalise column names.
    - Casts `Your_Rating` to `int` and `IMDb_Rating` to `float`; coerces errors to `NaN` rather than
      raising.
    - Parses `Date_Rated` and `Release_Date` as `datetime` objects with `errors="coerce"`.
    - Returns the cleaned DataFrame.
  - `filter_ratings(df, min_rating=1, max_rating=10, search_query="", selected_columns=None) -> pd.DataFrame`
    - Filters rows where `Your_Rating` is between `min_rating` and `max_rating` (inclusive).
    - Applies case-insensitive substring match on `Title` if `search_query` is non-empty.
    - Subsets columns to `selected_columns` if provided (returns all columns otherwise).
    - Operates on a copy — never mutates the input DataFrame.
    - Returns the filtered copy.
  - `export_to_excel_buffer(df: pd.DataFrame, sheet_name: str = "IMDb Ratings") -> io.BytesIO`
    - Uses `pd.DataFrame.to_excel` with `engine="openpyxl"` writing into an `io.BytesIO` buffer.
    - Seeks the buffer back to position 0 before returning.
    - Returns the `BytesIO` buffer.
- **Dependencies:** `pandas`, `openpyxl`, `src/utils/constants.py`.

#### 4.3 `src/services/analytics_service.py`
- **Purpose:** All taste-profile computations. Pure functions, no I/O, no Streamlit.
- **Key functions:**
  - `calculate_rating_distribution(df: pd.DataFrame) -> pd.DataFrame`
    - Counts occurrences of each integer score 1–10 in `Your_Rating`.
    - Reindexes over the full range `[1..10]` and fills missing scores with `0` so every bin is
      always present.
    - Returns DataFrame with columns `["Rating", "Count"]`.
  - `compute_genre_breakdown(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame`
    - Drops rows where `Genres` is null/empty before exploding.
    - Splits `Genres` on `", "` and explodes to one genre per row.
    - Groups by genre: aggregates `title_count` (count) and `avg_user_rating` (mean of `Your_Rating`).
    - Sorts by `title_count` descending, takes top `top_n`.
    - Returns DataFrame with columns `["Genre", "title_count", "avg_user_rating"]`.
  - `compute_critical_divergence(df: pd.DataFrame, threshold: float = 2.0) -> dict[str, pd.DataFrame]`
    - Drops rows where `IMDb_Rating` is null.
    - Computes `Delta = Your_Rating − IMDb_Rating`.
    - `hot_takes`: rows where `Delta >= threshold`, sorted by `Delta` descending.
    - `hidden_dislikes`: rows where `Delta <= −threshold`, sorted by `Delta` ascending.
    - Returns `{"hot_takes": ..., "hidden_dislikes": ...}`.
  - `suggest_hidden_gems(df: pd.DataFrame, min_user_rating: int = 8, max_imdb_rating: float = 7.0) -> pd.DataFrame`
    - Surfaces films the user rated highly that IMDb underestimates.
    - Filters rows where `Your_Rating >= min_user_rating` AND `IMDb_Rating <= max_imdb_rating`.
    - Adds a `Gap` column (`Your_Rating − IMDb_Rating`).
    - Sorts by `Your_Rating` descending, `IMDb_Rating` ascending as tiebreaker.
    - Returns filtered DataFrame; empty if no qualifying rows or missing columns.
- **Dependencies:** `pandas`, `src/utils/constants.py`.

---

### Step 5 — Streamlit UI Entry Point

#### 5.1 `app.py`
- **Purpose:** Single-file Streamlit application wiring all services to the UI. Contains no business
  logic — delegates every data operation to the service layer.
- **Key sections (implemented as sequential `st.*` calls within `app.py`):**
  - **Session State initialisation** — stores the active DataFrame in `st.session_state["df"]`.
  - **Sidebar — Ingestion Panel**
    - `st.text_input` for IMDb user ID; on submit calls `extract_user_id` then
      `fetch_ratings_by_user_id`; catches `UserListPrivateError` and `IMDbConnectionError` and
      surfaces them with `st.error()`.
    - `st.file_uploader` (`.csv` only); on upload calls `parse_imdb_csv`; catches `ValueError` and
      displays `st.toast()` error.
  - **Main area — Tab 1: Inspect & Filter**
    - `st.multiselect` for column selection.
    - `st.slider` for rating range (1–10).
    - `st.text_input` for title search.
    - Calls `filter_ratings` on every widget interaction; renders result with `st.dataframe`.
    - "Export CSV" button: calls `st.download_button` with `df.to_csv(index=False)` as `text/csv`.
    - "Export Excel" button: calls `export_to_excel_buffer`, passes result to `st.download_button`
      as `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
  - **Main area — Tab 2: Analytics Dashboard**
    - Calls `calculate_rating_distribution` → renders Altair bar chart + `st.metric` for mean,
      median, total count.
    - Calls `compute_genre_breakdown` → renders Altair horizontal bar chart.
    - Calls `compute_critical_divergence` → renders two `st.dataframe` tables side by side.
    - All analytics operate on the current filtered DataFrame (honours active filter state).
- **Dependencies:** `streamlit`, `altair`, `src/services/imdb_service.py`,
  `src/services/data_service.py`, `src/services/analytics_service.py`.

---

### Step 6 — Test Infrastructure

#### 6.1 `tests/conftest.py`
- **Purpose:** Shared pytest fixtures used across all test modules.
- **Key fixtures:**
  - `sample_csv_string` — a multi-row raw IMDb CSV string containing all 12 columns, with at least
    one row per rating score (1–10) and at least two genres per row.
  - `sample_df` — the parsed DataFrame produced by calling `parse_imdb_csv(sample_csv_string)`.
  - `minimal_csv_string` — a CSV string containing only the three required columns (`Const`,
    `Your Rating`, `Title`) to test minimal-valid input.
  - `missing_col_csv_string` — a CSV string with `Title` deliberately omitted to trigger validation
    failures.
  - `multi_genre_df` — a small DataFrame where `Genres` contains comma-separated strings like
    `"Action, Adventure, Sci-Fi"`.
- **Dependencies:** `src/services/data_service.py`, `pytest`.

---

## 2. UNIT TESTS

### `tests/test_imdb_service.py`

Co-locates network integration tests (mocked) alongside pure-logic unit tests.

| Test function | What it tests |
|---|---|
| `test_extract_user_id_valid_bare` | `"ur12345678"` → returns `"ur12345678"` |
| `test_extract_user_id_valid_url` | Full IMDb profile URL containing user ID → extracts and returns bare ID |
| `test_extract_user_id_invalid_no_prefix` | `"12345678"` (no `ur` prefix) → returns `None` |
| `test_extract_user_id_invalid_letters_in_digits` | `"ur123abc"` → returns `None` |
| `test_extract_user_id_empty_string` | `""` → returns `None` |
| `test_extract_user_id_whitespace_stripped` | `"  ur99  "` → returns `"ur99"` after strip |
| `test_fetch_ratings_200_returns_csv_text` | Mocked `requests.get` returning 200 with CSV body → function returns that CSV string |
| `test_fetch_ratings_403_raises_UserListPrivateError` | Mocked 403 response → `UserListPrivateError` raised |
| `test_fetch_ratings_404_raises_IMDbConnectionError` | Mocked 404 response → `IMDbConnectionError` raised |
| `test_fetch_ratings_500_raises_IMDbConnectionError` | Mocked 500 response → `IMDbConnectionError` raised |
| `test_fetch_ratings_uses_bs4_resolved_url` | HTML page mock with `<a>` CSV link present → BS4 extraction used and correct URL fetched |
| `test_fetch_ratings_falls_back_when_no_bs4_link` | HTML page mock with no `<a>` CSV link → falls back to template URL |

**Edge cases:**
- User ID with many digits (e.g. `ur000000001`).
- Network timeout (`requests.exceptions.Timeout`) should be converted to `IMDbConnectionError`.

---

### `tests/test_data_service.py`

Co-locates serialisation tests (openpyxl round-trip) alongside pure transformation unit tests.

| Test function | What it tests |
|---|---|
| `test_parse_imdb_csv_valid_string` | Valid CSV string → DataFrame with correct shape and dtypes |
| `test_parse_imdb_csv_valid_stringio` | Same CSV via `io.StringIO` → identical result |
| `test_parse_imdb_csv_valid_bytesio` | Same CSV via `io.BytesIO` → identical result |
| `test_parse_imdb_csv_missing_required_column` | CSV without `Title` → `ValueError` raised |
| `test_parse_imdb_csv_mixed_rating_types` | `Your Rating` column contains strings like `"7"` → cast to `int` |
| `test_parse_imdb_csv_malformed_imdb_rating` | `IMDb Rating` contains `"N/A"` → coerced to `NaN`, no exception |
| `test_parse_imdb_csv_malformed_date` | `Date Rated` contains `"not-a-date"` → coerced to `NaT`, no exception |
| `test_filter_ratings_min_boundary` | `min_rating=5` → no rows with `Your_Rating < 5` in output |
| `test_filter_ratings_max_boundary` | `max_rating=7` → no rows with `Your_Rating > 7` in output |
| `test_filter_ratings_full_range` | `min=1, max=10` → all rows returned |
| `test_filter_ratings_empty_result` | `min=11` (impossible) → empty DataFrame |
| `test_filter_ratings_search_case_insensitive` | Query `"shawshank"` matches `"The Shawshank Redemption"` |
| `test_filter_ratings_search_no_match` | Query `"zzznomatch"` → empty result |
| `test_filter_ratings_column_selection` | `selected_columns=["Title", "Your_Rating"]` → output has exactly those columns |
| `test_filter_ratings_does_not_mutate_input` | Input DataFrame unchanged after call |
| `test_export_to_excel_buffer_readable` | Returned `BytesIO` is readable by `openpyxl.load_workbook` |
| `test_export_to_excel_buffer_sheet_name` | Workbook sheet name equals `"IMDb Ratings"` |
| `test_export_to_excel_buffer_custom_sheet_name` | Custom `sheet_name` argument respected |
| `test_export_to_excel_buffer_stream_position_zero` | `buffer.tell() == 0` immediately after return |

**Edge cases:**
- Empty DataFrame passed to `filter_ratings` → empty DataFrame returned without error.
- DataFrame with a single row.

---

### `tests/test_analytics_service.py`

| Test function | What it tests |
|---|---|
| `test_rating_distribution_all_bins_present` | Output always has exactly 10 rows (1 per score) |
| `test_rating_distribution_zero_fill` | Score with no occurrence appears with `Count == 0` |
| `test_rating_distribution_correct_counts` | Known input → verify specific bin counts |
| `test_rating_distribution_columns` | Output has columns `["Rating", "Count"]` |
| `test_genre_breakdown_single_genre` | Row with `"Drama"` → genre `"Drama"` appears in output |
| `test_genre_breakdown_multi_genre_explosion` | `"Action, Adventure, Sci-Fi"` → three separate rows in output |
| `test_genre_breakdown_top_n_limit` | 15 unique genres in data, `top_n=10` → exactly 10 rows returned |
| `test_genre_breakdown_sorted_by_count` | First row has the highest `title_count` |
| `test_genre_breakdown_correct_avg_score` | Known ratings per genre → verify rounded average |
| `test_genre_breakdown_null_genres_skipped` | Rows with `NaN` in `Genres` do not raise; are silently excluded |
| `test_critical_divergence_hot_takes` | `Delta >= 2.0` rows appear in `"hot_takes"` key, sorted descending |
| `test_critical_divergence_hidden_dislikes` | `Delta <= -2.0` rows appear in `"hidden_dislikes"` key, sorted ascending |
| `test_critical_divergence_exact_threshold` | Row with `Delta == 2.0` is **included** in `hot_takes` (boundary inclusive) |
| `test_critical_divergence_below_threshold_excluded` | Row with `Delta == 1.9` is **excluded** from `hot_takes` |
| `test_critical_divergence_null_imdb_rating_skipped` | Rows with `NaN` in `IMDb_Rating` do not raise |
| `test_critical_divergence_empty_dataframe` | Empty input → both result keys contain empty DataFrames |
| `test_critical_divergence_returns_dict_keys` | Return value has exactly keys `"hot_takes"` and `"hidden_dislikes"` |

**Edge cases:**
- Negative `Delta` exactly at `-2.0` is included in `hidden_dislikes`.
- All `IMDb_Rating` values are null → both output DataFrames are empty.

---

## 3. INTEGRATION TESTS

Integration tests live inside the unit test files noted above. They verify two or more real components
working together with only external I/O mocked.

| Test file | Integration scenario |
|---|---|
| `tests/test_imdb_service.py` | `fetch_ratings_by_user_id` + `requests` + `BeautifulSoup` — real parsing logic, mocked HTTP via `unittest.mock.patch` on `requests.get`. Verifies the full ID → HTML parse → CSV URL resolve → CSV fetch pipeline with no real network calls. |
| `tests/test_data_service.py` | `parse_imdb_csv` output fed directly into `filter_ratings` → verifies that the normalised column names produced by the parser are correctly consumed by the filter logic. |
| `tests/test_data_service.py` | `filter_ratings` result fed directly into `export_to_excel_buffer` → verifies the full "filter then export" path produces an `openpyxl`-readable workbook. |
| `tests/test_analytics_service.py` | `parse_imdb_csv` output fed into all three analytics functions → verifies real parsed data is compatible with each analytics function's expected column names and types. |

---

## 4. FUNCTIONAL TESTS

Functional tests verify complete features as described in SPEC.md §2 acceptance criteria. They are
co-located in the unit test files and `conftest.py` via parametrised scenarios.

| Spec feature | Acceptance criterion | Implementing test |
|---|---|---|
| Feature 1 — IMDb ID ingestion | AC1: ID validates `^ur\d+$` | `test_extract_user_id_valid_bare`, `test_extract_user_id_invalid_*` |
| Feature 1 — IMDb ID ingestion | AC2: Public list → CSV retrieved | `test_fetch_ratings_200_returns_csv_text` |
| Feature 1 — IMDb ID ingestion | AC3: Private/unavailable → domain exception raised | `test_fetch_ratings_403_raises_UserListPrivateError`, `test_fetch_ratings_404_raises_IMDbConnectionError` |
| Feature 2 — CSV upload | AC2: Standard IMDb columns parsed | `test_parse_imdb_csv_valid_string` |
| Feature 2 — CSV upload | AC3: Missing required columns → `ValueError` | `test_parse_imdb_csv_missing_required_column` |
| Feature 3 — Filtering | AC2: Rating slider boundaries | `test_filter_ratings_min_boundary`, `test_filter_ratings_max_boundary` |
| Feature 3 — Filtering | AC3: Case-insensitive title search | `test_filter_ratings_search_case_insensitive` |
| Feature 3 — Filtering | AC1: Column selection | `test_filter_ratings_column_selection` |
| Feature 4 — Export | AC1: CSV export — correct content | `test_export_to_excel_buffer_readable` (CSV via `df.to_csv` is trivial; covered in E2E) |
| Feature 4 — Export | AC2: Excel export — correct sheet name | `test_export_to_excel_buffer_sheet_name` |
| Feature 5 — Analytics | AC1: All 1–10 bins present | `test_rating_distribution_all_bins_present`, `test_rating_distribution_zero_fill` |
| Feature 5 — Analytics | AC2: Genre explosion and ranking | `test_genre_breakdown_multi_genre_explosion`, `test_genre_breakdown_sorted_by_count` |
| Feature 5 — Analytics | AC3: Divergence thresholds inclusive | `test_critical_divergence_exact_threshold`, `test_critical_divergence_below_threshold_excluded` |

---

## 5. END-TO-END TESTS

### `tests/test_e2e.py`

Uses `streamlit.testing.v1.AppTest`. All tests start from a cold app state.

**Setup / teardown:**
- Each test creates a fresh `AppTest.from_file("app.py")` instance.
- No real network calls are made; where needed the IMDb service is patched via
  `unittest.mock.patch`.
- No files are written to disk.

| Test function | Workflow tested |
|---|---|
| `test_e2e_csv_upload_populates_dataframe` | Upload `sample_csv_string` via file uploader → assert `st.dataframe` component contains the expected number of rows |
| `test_e2e_filter_slider_reduces_rows` | Upload CSV, set rating slider to `min=8, max=10` → assert rendered row count is less than unfiltered total |
| `test_e2e_title_search_filters_results` | Upload CSV, type known title substring → assert only matching rows are displayed |
| `test_e2e_analytics_tab_renders_charts` | Upload CSV, switch to Analytics tab → assert Altair chart components and `st.metric` components are non-empty / non-null |
| `test_e2e_export_csv_button_present` | Upload CSV → assert "Export CSV" download button is rendered in the UI |
| `test_e2e_export_excel_button_present` | Upload CSV → assert "Export Excel" download button is rendered in the UI |
| `test_e2e_invalid_user_id_shows_error` | Enter `"invalid123"` in user ID field → assert `st.error` component is displayed |
| `test_e2e_private_list_shows_error` | Patch `fetch_ratings_by_user_id` to raise `UserListPrivateError` → assert `st.error` displayed |
| `test_e2e_missing_columns_shows_toast` | Upload CSV missing `Title` column → assert `st.toast` error is displayed |

---

## 6. HOW TO RUN THE APPLICATION

### Environment Setup

```bash
# Windows (PowerShell — matches this project's environment)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install all dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Run the Application

```bash
# Ensure the virtual environment is active, then:
streamlit run app.py
# Open http://localhost:8501 in your browser
```

**Expected output when working:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://<your-ip>:8501
```
The browser opens the CineTrack Local dashboard with a sidebar offering IMDb user ID entry and a CSV
file uploader, and a two-tab main area ("Inspect & Filter" and "Analytics Dashboard").

---

### Run Unit + Integration Tests

```bash
pytest tests/test_imdb_service.py tests/test_data_service.py tests/test_analytics_service.py -v
```

**Expected output when passing:**
```
tests/test_imdb_service.py::test_extract_user_id_valid_bare_numeric PASSED
...
tests/test_analytics_service.py::test_hidden_gems_integration PASSED

89 passed in X.XXs
```

### Run End-to-End Tests

```bash
pytest tests/test_e2e.py -v
```

**Expected output when passing:**
```
tests/test_e2e.py::test_e2e_csv_upload_populates_dataframe PASSED
...
tests/test_e2e.py::test_e2e_missing_columns_shows_toast PASSED

9 passed in X.XXs
```

### Run All Tests at Once

```bash
pytest tests/ -v
```

### Run Tests with Coverage Report

```bash
pip install pytest-cov   # one-time install
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Sub-Task Status Tracker

| # | Sub-task | Status |
|---|---|---|
| 1 | Create `requirements.txt`, `.gitignore`, `README.md` | [x] done |
| 2 | Create all `__init__.py` package files | [x] done |
| 3 | Implement `src/utils/constants.py` | [x] done |
| 4 | Implement `src/services/imdb_service.py` | [x] done |
| 5 | Implement `src/services/data_service.py` | [x] done |
| 6 | Implement `src/services/analytics_service.py` | [x] done |
| 7 | Implement `app.py` | [x] done |
| 8 | Implement `tests/conftest.py` | [x] done |
| 9 | Implement `tests/test_imdb_service.py` | [x] done |
| 10 | Implement `tests/test_data_service.py` | [x] done |
| 11 | Implement `tests/test_analytics_service.py` | [x] done |
| 12 | Implement `tests/test_e2e.py` | [x] done |
| 13 | Post-launch: `suggest_hidden_gems` + UI section + 11 new tests | [x] done |
