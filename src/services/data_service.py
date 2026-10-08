# src/services/data_service.py
# CSV ingestion, DataFrame normalisation, filtering, and in-memory export.
# No Streamlit imports — all functions are pure and independently testable.

import io

import pandas as pd

from src.utils.constants import COLUMN_RENAME_MAP, REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Ingestion & parsing
# ---------------------------------------------------------------------------


def parse_imdb_csv(raw_csv_source: str | io.BytesIO | io.StringIO) -> pd.DataFrame:
    """
    Parses CSV inputs into a standardised pandas DataFrame.

    Accepts a raw CSV string, io.BytesIO, or io.StringIO.
    Validates that REQUIRED_COLUMNS are present; raises ValueError otherwise.
    Normalises column names via COLUMN_RENAME_MAP.
    Casts Your_Rating to int and IMDb_Rating to float (coercing errors to NaN).
    Parses date columns with errors='coerce' (malformed dates become NaT).
    """
    # Normalise input type so pd.read_csv always receives a file-like object.
    if isinstance(raw_csv_source, str):
        source = io.StringIO(raw_csv_source)
    elif isinstance(raw_csv_source, bytes):
        source = io.BytesIO(raw_csv_source)
    else:
        source = raw_csv_source

    df = pd.read_csv(source)

    # Validate required columns.
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"The uploaded CSV is missing required column(s): {', '.join(missing)}. "
            "Please use a standard IMDb ratings export."
        )

    # Rename to normalised names (only rename columns that are present).
    rename = {k: v for k, v in COLUMN_RENAME_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Type casting — coerce rather than raise on bad values.
    if "Your_Rating" in df.columns:
        df["Your_Rating"] = pd.to_numeric(df["Your_Rating"], errors="coerce").astype(
            "Int64"  # nullable integer to handle NaN cleanly
        )

    if "IMDb_Rating" in df.columns:
        df["IMDb_Rating"] = pd.to_numeric(df["IMDb_Rating"], errors="coerce")

    if "Runtime_Mins" in df.columns:
        df["Runtime_Mins"] = pd.to_numeric(df["Runtime_Mins"], errors="coerce")

    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    # Date parsing.
    for date_col in ("Date_Rated", "Release_Date"):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_ratings(
    df: pd.DataFrame,
    min_rating: int = 1,
    max_rating: int = 10,
    search_query: str = "",
    selected_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Applies score boundaries, title substring search, and column filtering.

    Operates on a copy — never mutates the input DataFrame.
    Returns a sliced, copy-safe DataFrame.
    """
    result = df.copy()

    # Rating range filter (inclusive on both ends).
    if "Your_Rating" in result.columns:
        result = result[
            (result["Your_Rating"] >= min_rating) & (result["Your_Rating"] <= max_rating)
        ]

    # Case-insensitive title substring search.
    if search_query and "Title" in result.columns:
        mask = result["Title"].str.contains(search_query, case=False, na=False)
        result = result[mask]

    # Column selection.
    if selected_columns is not None:
        # Keep only columns that actually exist in the DataFrame.
        valid_cols = [c for c in selected_columns if c in result.columns]
        result = result[valid_cols]

    return result.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_to_excel_buffer(
    df: pd.DataFrame, sheet_name: str = "IMDb Ratings"
) -> io.BytesIO:
    """
    Serialises a DataFrame to an in-memory OpenPyXL Excel buffer.
    Returns io.BytesIO positioned at stream start (seek(0)).
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer
