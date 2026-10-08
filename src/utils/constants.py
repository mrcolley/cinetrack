# src/utils/constants.py
# Shared literals used across services and tests.

# --- IMDb URL templates ---

IMDB_USER_PAGE_URL = "https://www.imdb.com/user/{user_id}/ratings"
IMDB_EXPORT_URL = "https://www.imdb.com/user/{user_id}/ratings/export"

# --- Column validation ---

# The three columns that MUST be present in any uploaded / fetched CSV.
REQUIRED_COLUMNS = ["Const", "Your Rating", "Title"]

# --- Column name normalisation ---

# Maps the raw IMDb CSV header names to Python-friendly snake_case equivalents.
COLUMN_RENAME_MAP = {
    "Const": "Const",
    "Your Rating": "Your_Rating",
    "Date Rated": "Date_Rated",
    "Title": "Title",
    "URL": "URL",
    "Title Type": "Title_Type",
    "IMDb Rating": "IMDb_Rating",
    "Runtime (mins)": "Runtime_Mins",
    "Year": "Year",
    "Genres": "Genres",
    "Release Date": "Release_Date",
    "Directors": "Directors",
}

# Ordered list of all normalised RatingRecord field names (SPEC §4).
ALL_COLUMNS = [
    "Const",
    "Your_Rating",
    "Date_Rated",
    "Title",
    "URL",
    "Title_Type",
    "IMDb_Rating",
    "Runtime_Mins",
    "Year",
    "Genres",
    "Release_Date",
    "Directors",
]
