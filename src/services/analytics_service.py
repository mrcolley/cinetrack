# src/services/analytics_service.py
# Taste-profile computations: rating distribution, genre affinity, critical divergence.
# Pure functions — no I/O, no Streamlit, tolerant of missing/null data.

import pandas as pd


# ---------------------------------------------------------------------------
# Rating distribution
# ---------------------------------------------------------------------------


def calculate_rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes frequency distribution across integer scores 1 through 10.

    Always returns all 10 bins; scores with no occurrences receive Count=0.
    Returns DataFrame with columns ['Rating', 'Count'].
    """
    if "Your_Rating" not in df.columns or df.empty:
        # Return a zeroed-out full distribution.
        return pd.DataFrame({"Rating": range(1, 11), "Count": [0] * 10})

    counts = (
        df["Your_Rating"]
        .dropna()
        .astype(int)
        .value_counts()
        .reindex(range(1, 11), fill_value=0)
        .reset_index()
    )
    counts.columns = ["Rating", "Count"]
    counts = counts.sort_values("Rating").reset_index(drop=True)
    return counts


# ---------------------------------------------------------------------------
# Genre breakdown
# ---------------------------------------------------------------------------


def compute_genre_breakdown(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Splits comma-separated 'Genres', groups by individual genre, and aggregates
    title count and mean user score.

    Returns DataFrame with columns ['Genre', 'title_count', 'avg_user_rating']
    sorted by title_count descending, limited to top_n rows.

    Rows with null/empty Genres are silently excluded.
    """
    if "Genres" not in df.columns or df.empty:
        return pd.DataFrame(columns=["Genre", "title_count", "avg_user_rating"])

    # Drop rows with no genre data.
    genre_df = df[df["Genres"].notna() & (df["Genres"].str.strip() != "")].copy()

    if genre_df.empty:
        return pd.DataFrame(columns=["Genre", "title_count", "avg_user_rating"])

    # Explode comma-separated genres into individual rows.
    genre_df["Genre"] = genre_df["Genres"].str.split(r",\s*")
    genre_df = genre_df.explode("Genre")
    genre_df["Genre"] = genre_df["Genre"].str.strip()

    # Aggregate.
    aggregated = (
        genre_df.groupby("Genre", as_index=False)
        .agg(
            title_count=("Title", "count"),
            avg_user_rating=("Your_Rating", "mean"),
        )
        .sort_values("title_count", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    aggregated["avg_user_rating"] = aggregated["avg_user_rating"].round(2)
    return aggregated


# ---------------------------------------------------------------------------
# Critical divergence
# ---------------------------------------------------------------------------


def compute_critical_divergence(
    df: pd.DataFrame, threshold: float = 2.0
) -> dict[str, pd.DataFrame]:
    """
    Calculates divergence Delta = Your_Rating − IMDb_Rating for each title.

    Returns a dict with:
      - 'hot_takes':       rows where Delta >= threshold, sorted by Delta descending.
      - 'hidden_dislikes': rows where Delta <= -threshold, sorted by Delta ascending.

    Rows with null IMDb_Rating are excluded. An empty DataFrame is returned for
    either key if no qualifying rows exist.
    """
    empty = pd.DataFrame()

    required = {"Your_Rating", "IMDb_Rating"}
    if not required.issubset(df.columns) or df.empty:
        return {"hot_takes": empty, "hidden_dislikes": empty}

    # Work on a copy; drop rows where IMDb_Rating is missing.
    work = df.dropna(subset=["IMDb_Rating"]).copy()

    if work.empty:
        return {"hot_takes": empty, "hidden_dislikes": empty}

    work["Delta"] = work["Your_Rating"].astype(float) - work["IMDb_Rating"].astype(float)

    hot_takes = (
        work[work["Delta"] >= threshold]
        .sort_values("Delta", ascending=False)
        .reset_index(drop=True)
    )

    hidden_dislikes = (
        work[work["Delta"] <= -threshold]
        .sort_values("Delta", ascending=True)
        .reset_index(drop=True)
    )

    return {"hot_takes": hot_takes, "hidden_dislikes": hidden_dislikes}
