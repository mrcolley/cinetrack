# tests/conftest.py
# Shared pytest fixtures used across all test modules.

import io

import pandas as pd
import pytest

from src.services.data_service import parse_imdb_csv

# ---------------------------------------------------------------------------
# Raw CSV strings
# ---------------------------------------------------------------------------

# Full 12-column IMDb export with 10 rows — one per rating score (1–10).
# Multi-genre entries are included to support genre-explosion tests.
SAMPLE_CSV = """Const,Your Rating,Date Rated,Title,URL,Title Type,IMDb Rating,Runtime (mins),Year,Genres,Release Date,Directors
tt0000001,1,2024-01-01,Title One,https://www.imdb.com/title/tt0000001/,Movie,3.1,90,2000,Drama,2000-01-01,Director A
tt0000002,2,2024-01-02,Title Two,https://www.imdb.com/title/tt0000002/,Movie,4.2,95,2001,Comedy,2001-01-01,Director B
tt0000003,3,2024-01-03,Title Three,https://www.imdb.com/title/tt0000003/,Movie,5.3,100,2002,Action,2002-01-01,Director C
tt0000004,4,2024-01-04,Title Four,https://www.imdb.com/title/tt0000004/,Movie,6.4,105,2003,"Action, Adventure",2003-01-01,Director D
tt0000005,5,2024-01-05,The Shawshank Redemption,https://www.imdb.com/title/tt0000005/,Movie,9.3,142,1994,Drama,1994-10-14,Frank Darabont
tt0000006,6,2024-01-06,Title Six,https://www.imdb.com/title/tt0000006/,Movie,7.6,120,2005,"Sci-Fi, Thriller",2005-01-01,Director F
tt0000007,7,2024-01-07,Title Seven,https://www.imdb.com/title/tt0000007/,TV Series,6.7,45,2006,"Drama, Comedy",2006-01-01,Director G
tt0000008,8,2024-01-08,Title Eight,https://www.imdb.com/title/tt0000008/,Movie,5.8,110,2007,Horror,2007-01-01,Director H
tt0000009,9,2024-01-09,Title Nine,https://www.imdb.com/title/tt0000009/,Movie,4.9,130,2008,"Action, Adventure, Sci-Fi",2008-01-01,Director I
tt0000010,10,2024-01-10,Title Ten,https://www.imdb.com/title/tt0000010/,Movie,8.0,150,2009,Thriller,2009-01-01,Director J
"""

# Minimal valid CSV — only the three required columns.
MINIMAL_CSV = """Const,Your Rating,Title
tt1111111,7,Minimal Movie
tt2222222,9,Another Movie
"""

# CSV with the Title column deliberately missing — should trigger ValueError.
MISSING_COL_CSV = """Const,Your Rating,Date Rated
tt3333333,5,2024-06-01
"""

# CSV with a multi-genre string for genre-explosion tests.
MULTI_GENRE_CSV = """Const,Your Rating,Date Rated,Title,URL,Title Type,IMDb Rating,Runtime (mins),Year,Genres,Release Date,Directors
tt9000001,8,2024-02-01,Action Movie,https://www.imdb.com/title/tt9000001/,Movie,7.5,120,2020,"Action, Adventure, Sci-Fi",2020-01-01,Director X
tt9000002,6,2024-02-02,Drama Movie,https://www.imdb.com/title/tt9000002/,Movie,6.0,100,2019,Drama,2019-01-01,Director Y
tt9000003,9,2024-02-03,Comedy Action,https://www.imdb.com/title/tt9000003/,Movie,8.0,110,2021,"Action, Comedy",2021-01-01,Director Z
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv_string() -> str:
    """Raw IMDb CSV string with all 12 columns and 10 rows (one per rating score)."""
    return SAMPLE_CSV


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Parsed DataFrame from SAMPLE_CSV — the standard fixture for most tests."""
    return parse_imdb_csv(SAMPLE_CSV)


@pytest.fixture
def minimal_csv_string() -> str:
    """CSV with only the three required columns — tests minimal-valid input."""
    return MINIMAL_CSV


@pytest.fixture
def missing_col_csv_string() -> str:
    """CSV missing the Title column — should trigger ValueError in parse_imdb_csv."""
    return MISSING_COL_CSV


@pytest.fixture
def multi_genre_df() -> pd.DataFrame:
    """Parsed DataFrame with multi-genre entries for genre explosion tests."""
    return parse_imdb_csv(MULTI_GENRE_CSV)


@pytest.fixture
def sample_csv_bytesio() -> io.BytesIO:
    """SAMPLE_CSV as an io.BytesIO stream."""
    return io.BytesIO(SAMPLE_CSV.encode("utf-8"))


@pytest.fixture
def sample_csv_stringio() -> io.StringIO:
    """SAMPLE_CSV as an io.StringIO stream."""
    return io.StringIO(SAMPLE_CSV)
