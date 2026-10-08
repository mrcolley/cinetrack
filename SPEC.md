# Software Requirements Specification (SRS): CineTrack Local

## 1. Application Name & Purpose

**CineTrack Local** is a local-first web application that allows users to import their IMDb movie ratings via user identifier or direct CSV export, inspect and filter records, analyze their taste through a taste profile and ratings analytics dashboard, and export the structured datasets into cleanly formatted CSV and Excel files.

---

## 2. Feature List & Acceptance Criteria

### Feature 1: Ingestion via IMDb Identifier

* **Description:** The user enters their public IMDb user ID (e.g., `ur12345678`) to download rating history directly.
* **Acceptance Criteria:**
1. Input field validates that the ID matches the format `^ur\d+$`.
2. If the user list is public, the application retrieves the dataset from the IMDb export endpoint.
3. If the user list is private or unavailable (HTTP non-200), the UI presents a non-crashing error notification explaining list privacy restrictions.
4. Successfully parsed data populates the in-memory tabular viewer.



### Feature 2: Ingestion via Direct File Upload

* **Description:** The user uploads a native `ratings.csv` file directly exported from IMDb.
* **Acceptance Criteria:**
1. Accepts only `.csv` file formats.
2. Parses standard IMDb column headers (`Const`, `Your Rating`, `Date Rated`, `Title`, etc.).
3. Displays an error toast if required columns are absent or the file is corrupted.
4. Overwrites or updates the active session dataframe upon successful upload.



### Feature 3: Data Inspection & Filtering

* **Description:** Dynamic controls to manipulate visible records in real time.
* **Acceptance Criteria:**
1. Multi-select component permits adding/removing columns from the view dynamically.
2. Rating slider filters rows where `Your Rating` is between user-selected min and max boundaries ($1 \le \text{rating} \le 10$).
3. Text search field performs a case-insensitive substring match on the `Title` column.
4. Display updates instantaneously without triggering network requests.



### Feature 4: Formatted File Export

* **Description:** Generation and download of the filtered view into external files.
* **Acceptance Criteria:**
1. "Export CSV" generates a standard UTF-8 encoded `.csv` containing only currently visible, filtered rows and selected columns.
2. "Export Excel" produces a valid `.xlsx` file containing a named worksheet (`IMDb Ratings`) preserving string/numeric types.
3. File downloads trigger directly via standard browser save dialogues without disk writes on the server/host machine.



### Feature 5: Taste Profile & Rating Analytics Dashboard

* **Description:** An interactive analytics suite that decomposes user viewing habits, rating distribution, genre affinities, and critical divergence.
* **Acceptance Criteria:**
1. **Rating Distribution:** Displays a bar chart plotting score frequency from 1 to 10 with summary metrics (mean user rating, median, total rated titles).
2. **Genre Affinity:** Explodes comma-delimited `Genres`, aggregating and ranking the top 10 genres by total titles watched and average user score per genre.
3. **Critical Divergence Matrix:** Calculates $\Delta = \text{Your Rating} - \text{IMDb Rating}$ for each title:
* Isolates the user's top "Overrated by You" titles ($\Delta \ge +2.0$, sorted descending).
* Isolates the user's top "Underrated by You" titles ($\Delta \le -2.0$, sorted ascending).


4. Visual charts update dynamically based on the currently applied filters.



---

## 3. Technology Stack & Pinned Versions

| Layer | Dependency | Exact Version | Purpose |
| --- | --- | --- | --- |
| **Runtime** | Python | `3.11.x` | Base runtime environment |
| **UI Framework** | `streamlit` | `1.38.0` | Local dashboard and presentation layer |
| **Data Engine** | `pandas` | `2.2.2` | Dataframe transformation and tabular manipulation |
| **Visualization** | `altair` | `5.4.1` | Native declarative charting integrated with Streamlit |
| **Excel Engine** | `openpyxl` | `3.1.5` | Spreadsheet serialization backend for Pandas |
| **HTTP Client** | `requests` | `2.32.3` | Ingestion fetcher for remote IMDb endpoints |
| **HTML Parser** | `beautifulsoup4` | `4.12.3` | Secondary DOM verification / scraper utilities |
| **Test Engine** | `pytest` | `8.3.2` | Unit and integration test runner |

---

## 4. Data Model

The primary data entity is the **RatingRecord**, parsed from IMDb's standard schema.

| Field Name | Type | Nullable | Description | Example |
| --- | --- | --- | --- | --- |
| `Const` | String | No | IMDb unique identifier (Alpha-numeric) | `"tt0111161"` |
| `Your_Rating` | Integer | No | User-assigned score ($1 \le x \le 10$) | `10` |
| `Date_Rated` | Date | No | Date user scored title (`YYYY-MM-DD`) | `"2024-01-15"` |
| `Title` | String | No | Official movie or show title | `"The Shawshank Redemption"` |
| `URL` | String | Yes | Link to IMDb title page | `"[https://www.imdb.com/title/tt0111161/](https://www.imdb.com/title/tt0111161/)"` |
| `Title_Type` | String | Yes | Media type (`Movie`, `TV Series`, etc.) | `"Movie"` |
| `IMDb_Rating` | Float | Yes | Global community rating ($0.0 \le x \le 10.0$) | `9.3` |
| `Runtime_Mins` | Float | Yes | Running length in minutes | `142.0` |
| `Year` | Integer | Yes | Release year | `1994` |
| `Genres` | String | Yes | Comma-separated list of genres | `"Drama"` |
| `Release_Date` | Date | Yes | Theatrical release date | `"1994-10-14"` |
| `Directors` | String | Yes | Comma-separated list of directors | `"Frank Darabont"` |

---

## 5. API & Function Signatures

All core business logic resides in standalone, testable functions isolated from the Streamlit UI state.

```python
# Location: src/services/imdb_service.py

def extract_user_id(raw_input: str) -> str | None:
    """
    Extracts and normalizes the IMDb user identifier matching 'ur' + digits.
    Returns normalized 'urXXXXXXX' or None if invalid.
    """
    pass

def fetch_ratings_by_user_id(user_id: str, timeout: int = 10) -> str:
    """
    Executes an HTTP GET request to IMDb's export URL for the specified user_id.
    Raises requests.exceptions.HTTPError if non-200.
    Returns raw CSV text payload.
    """
    pass

# Location: src/services/data_service.py

def parse_imdb_csv(raw_csv_source: str | io.BytesIO | io.StringIO) -> pd.DataFrame:
    """
    Parses CSV inputs into a standardized pandas DataFrame.
    Validates presence of core columns: ['Const', 'Your Rating', 'Title'].
    Enforces numeric casting on 'Your Rating' and 'IMDb Rating'.
    """
    pass

def filter_ratings(
    df: pd.DataFrame, 
    min_rating: int = 1, 
    max_rating: int = 10, 
    search_query: str = "", 
    selected_columns: list[str] | None = None
) -> pd.DataFrame:
    """
    Applies score boundaries, title substring search, and column filtering.
    Returns a sliced, copy-safe DataFrame.
    """
    pass

def export_to_excel_buffer(df: pd.DataFrame, sheet_name: str = "IMDb Ratings") -> io.BytesIO:
    """
    Serializes a DataFrame to an in-memory OpenPyXL Excel buffer.
    Returns io.BytesIO positioned at stream start (seek(0)).
    """
    pass

# Location: src/services/analytics_service.py

def calculate_rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes frequency distribution across integer scores 1 through 10.
    Returns DataFrame with columns ['Rating', 'Count'].
    """
    pass

def compute_genre_breakdown(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Splits comma-separated 'Genres', groups by individual genre, and aggregates
    title count and mean user score. Returns DataFrame sorted by title count descending.
    """
    pass

def compute_critical_divergence(df: pd.DataFrame, threshold: float = 2.0) -> dict[str, pd.DataFrame]:
    """
    Calculates divergence Delta = (Your Rating - IMDb Rating).
    Returns a dict with:
      - 'hot_takes': df where Delta >= threshold, sorted by Delta descending.
      - 'hidden_dislikes': df where Delta <= -threshold, sorted by Delta ascending.
    """
    pass

```

---

## 6. Virtual Environment Setup Instructions

Execute in terminal:

```bash
# 1. Create target directory and enter
mkdir cinetrack-local && cd cinetrack-local

# 2. Instantiate isolated Python 3.11 virtual environment
python3.11 -m venv .venv

# 3. Activate the environment
# Linux/macOS:
source .venv/bin/activate
# Windows (CMD):
# .venv\Scripts\activate.bat
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 4. Verify local Python binary
which python # Must point to .venv/bin/python

# 5. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

```

---

## 7. Directory & File Structure

```
cinetrack-local/
├── .venv/                      # Isolated virtual environment (ignored in git)
├── .gitignore                  # Standard Python gitignore
├── requirements.txt            # Pinned dependency manifest
├── README.md                   # Documentation
├── app.py                      # Main Streamlit UI entrypoint
├── src/
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── imdb_service.py      # Network and ingestion logic
│   │   ├── data_service.py      # Transformation, filtering, and export logic
│   │   └── analytics_service.py # Taste profile, distributions, and divergence logic
│   └── utils/
│       ├── __init__.py
│       └── constants.py         # Default schemas, column names, headers
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures (mock CSV strings, sample data)
    ├── test_imdb_service.py     # Regex & network unit tests
    ├── test_data_service.py     # Parsing, filtering, and serialization unit tests
    └── test_analytics_service.py# Taste metrics and divergence calculation unit tests

```

---

## 8. Error Handling Philosophy

1. **Defensive Parsing:** Never assume standard CSV format invariants from external sources. Wrap CSV ingestion in schema validation blocks; drop or handle malformed dates gracefully without failing the entire batch.
2. **Graceful Network Degradation:** HTTP requests must define strict timeouts (`timeout=10`). Failures (e.g., 403 Forbidden, 404 Not Found, DNS resolution failure) must be caught and converted into actionable domain exceptions (`UserListPrivateError`, `IMDbConnectionError`), which surface in the UI via `st.error()` rather than raw tracebacks.
3. **Stateless Transformations:** Filtering and export operations must operate idempotently on copies of the data; mutated session states must never lock the UI on bad filter configurations.
4. **Resilient Aggregations:** Analytics functions must tolerate missing columns (e.g., missing `IMDb Rating` or blank `Genres`) by imputing or skipping null records rather than raising unhandled `KeyError` or type errors.
5. **Zero Local Leaks:** The app processes data exclusively in-memory (`io.StringIO`, `io.BytesIO`). Do not write temporary data files to host disk to eliminate file cleanup requirements and path conflicts.

---

## 9. Testing Requirements

### Unit Testing (`tests/test_data_service.py`, `tests/test_imdb_service.py`, `tests/test_analytics_service.py`)

* `extract_user_id`: Test with full URLs, raw IDs, malformed inputs, and empty strings.
* `parse_imdb_csv`: Test with valid IMDb exports, missing required columns (assert raise), and mixed-type ratings.
* `filter_ratings`: Validate rating range edge cases (1, 10), case-insensitive partial substring match, and column filtering.
* `export_to_excel_buffer`: Assert returned stream is readable by `openpyxl.load_workbook` and check sheet name matching.
* `calculate_rating_distribution`: Verify output retains complete 1–10 bins even when specific ratings contain 0 occurrences.
* `compute_genre_breakdown`: Test explosion of multi-genre strings (e.g., `"Action, Adventure, Sci-Fi"`) and verify correct average score rounding.
* `compute_critical_divergence`: Test divergence sorting with positive and negative deltas, including exact floating-point threshold comparisons.

### Integration Testing

* Mock network responses using `unittest.mock` / `responses` to assert `fetch_ratings_by_user_id` properly returns text data on 200 and raises appropriate exceptions on 404/500 without making real network calls.

### End-to-End Testing

* Execute end-to-end smoke verification using `streamlit.testing.v1.AppTest`:
* Initialize `AppTest` against `app.py`.
* Inject file upload into file uploader component.
* Verify dataframe component contains parsed rows.
* Switch to the Analytics view and assert that chart and metric components render non-null states.
* Adjust rating filter sliders and verify rendered item counts decrease proportionally.



---

## 10. How to Run the Application Locally

```bash
# 1. Ensure the virtual environment is activated
source .venv/bin/activate

# 2. Run the application via Streamlit
streamlit run app.py

# 3. Access the dashboard
# Open your browser to http://localhost:8501

```