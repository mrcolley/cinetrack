# tests/test_analytics_service.py
# Unit tests for calculate_rating_distribution, compute_genre_breakdown,
# and compute_critical_divergence.
# Also includes integration tests: parse_imdb_csv output fed into analytics functions.

import pandas as pd
import pytest

from src.services.analytics_service import (
    calculate_rating_distribution,
    compute_critical_divergence,
    compute_genre_breakdown,
    suggest_hidden_gems,
)
from src.services.data_service import parse_imdb_csv

# ---------------------------------------------------------------------------
# calculate_rating_distribution
# ---------------------------------------------------------------------------


def test_rating_distribution_all_bins_present(sample_df):
    result = calculate_rating_distribution(sample_df)
    assert len(result) == 10
    assert set(result["Rating"]) == set(range(1, 11))


def test_rating_distribution_zero_fill():
    # DataFrame with only ratings 1, 2, 3 — bins 4–10 must be 0.
    df = pd.DataFrame({"Your_Rating": [1, 1, 2, 3]})
    result = calculate_rating_distribution(df)
    assert len(result) == 10
    zero_bins = result[result["Rating"] > 3]["Count"]
    assert (zero_bins == 0).all()


def test_rating_distribution_correct_counts(sample_df):
    # sample_df has exactly one row per rating 1–10.
    result = calculate_rating_distribution(sample_df)
    assert (result["Count"] == 1).all()


def test_rating_distribution_columns(sample_df):
    result = calculate_rating_distribution(sample_df)
    assert list(result.columns) == ["Rating", "Count"]


def test_rating_distribution_empty_dataframe():
    result = calculate_rating_distribution(pd.DataFrame())
    assert len(result) == 10
    assert (result["Count"] == 0).all()


def test_rating_distribution_all_same_rating():
    df = pd.DataFrame({"Your_Rating": [7, 7, 7, 7]})
    result = calculate_rating_distribution(df)
    assert result[result["Rating"] == 7]["Count"].iloc[0] == 4
    assert result[result["Rating"] != 7]["Count"].sum() == 0


def test_rating_distribution_sorted_ascending(sample_df):
    result = calculate_rating_distribution(sample_df)
    assert list(result["Rating"]) == list(range(1, 11))


# ---------------------------------------------------------------------------
# compute_genre_breakdown
# ---------------------------------------------------------------------------


def test_genre_breakdown_single_genre(sample_df):
    result = compute_genre_breakdown(sample_df)
    genre_names = result["Genre"].tolist()
    assert "Drama" in genre_names


def test_genre_breakdown_multi_genre_explosion(multi_genre_df):
    result = compute_genre_breakdown(multi_genre_df)
    genre_names = result["Genre"].tolist()
    # "Action, Adventure, Sci-Fi" should produce all three as separate genres.
    assert "Action" in genre_names
    assert "Adventure" in genre_names
    assert "Sci-Fi" in genre_names


def test_genre_breakdown_top_n_limit(sample_df):
    result = compute_genre_breakdown(sample_df, top_n=3)
    assert len(result) <= 3


def test_genre_breakdown_sorted_by_count(sample_df):
    result = compute_genre_breakdown(sample_df, top_n=10)
    counts = result["title_count"].tolist()
    assert counts == sorted(counts, reverse=True)


def test_genre_breakdown_correct_avg_score(multi_genre_df):
    # In multi_genre_df, "Drama" appears once with rating 6.
    result = compute_genre_breakdown(multi_genre_df)
    drama_row = result[result["Genre"] == "Drama"]
    assert not drama_row.empty
    assert drama_row["avg_user_rating"].iloc[0] == 6.0


def test_genre_breakdown_null_genres_skipped():
    df = pd.DataFrame({
        "Title": ["A", "B", "C"],
        "Your_Rating": [7, 8, 9],
        "Genres": ["Drama", None, ""],
    })
    # Should not raise; null/empty genres silently excluded.
    result = compute_genre_breakdown(df)
    assert "Drama" in result["Genre"].tolist()
    assert len(result) == 1


def test_genre_breakdown_columns(sample_df):
    result = compute_genre_breakdown(sample_df)
    assert list(result.columns) == ["Genre", "title_count", "avg_user_rating"]


def test_genre_breakdown_empty_dataframe():
    result = compute_genre_breakdown(pd.DataFrame())
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# compute_critical_divergence
# ---------------------------------------------------------------------------


def _make_divergence_df(deltas: list[float]) -> pd.DataFrame:
    """Helper: build a DataFrame with explicit Delta values via Your_Rating and IMDb_Rating."""
    rows = []
    for i, delta in enumerate(deltas):
        imdb = 7.0
        your = imdb + delta
        rows.append({
            "Title": f"Movie {i}",
            "Your_Rating": your,
            "IMDb_Rating": imdb,
        })
    return pd.DataFrame(rows)


def test_critical_divergence_returns_dict_keys(sample_df):
    result = compute_critical_divergence(sample_df)
    assert set(result.keys()) == {"hot_takes", "hidden_dislikes"}


def test_critical_divergence_hot_takes():
    df = _make_divergence_df([3.0, 1.0, -1.0, -3.0])
    result = compute_critical_divergence(df)
    hot = result["hot_takes"]
    assert len(hot) == 1
    assert hot["Delta"].iloc[0] == 3.0


def test_critical_divergence_hidden_dislikes():
    df = _make_divergence_df([3.0, 1.0, -1.0, -3.0])
    result = compute_critical_divergence(df)
    cold = result["hidden_dislikes"]
    assert len(cold) == 1
    assert cold["Delta"].iloc[0] == -3.0


def test_critical_divergence_exact_threshold_included():
    """Delta == 2.0 must be INCLUDED in hot_takes (boundary is inclusive)."""
    df = _make_divergence_df([2.0])
    result = compute_critical_divergence(df, threshold=2.0)
    assert len(result["hot_takes"]) == 1


def test_critical_divergence_exact_negative_threshold_included():
    """Delta == -2.0 must be INCLUDED in hidden_dislikes."""
    df = _make_divergence_df([-2.0])
    result = compute_critical_divergence(df, threshold=2.0)
    assert len(result["hidden_dislikes"]) == 1


def test_critical_divergence_below_threshold_excluded():
    """Delta == 1.9 must NOT appear in hot_takes."""
    df = _make_divergence_df([1.9])
    result = compute_critical_divergence(df, threshold=2.0)
    assert len(result["hot_takes"]) == 0


def test_critical_divergence_hot_takes_sorted_descending():
    df = _make_divergence_df([2.5, 4.0, 3.1])
    result = compute_critical_divergence(df)
    deltas = result["hot_takes"]["Delta"].tolist()
    assert deltas == sorted(deltas, reverse=True)


def test_critical_divergence_hidden_dislikes_sorted_ascending():
    df = _make_divergence_df([-2.5, -4.0, -3.1])
    result = compute_critical_divergence(df)
    deltas = result["hidden_dislikes"]["Delta"].tolist()
    assert deltas == sorted(deltas)


def test_critical_divergence_null_imdb_rating_skipped():
    df = pd.DataFrame({
        "Title": ["A", "B"],
        "Your_Rating": [9.0, 5.0],
        "IMDb_Rating": [None, 7.0],
    })
    # Should not raise; row with None IMDb_Rating is excluded.
    result = compute_critical_divergence(df)
    assert isinstance(result["hot_takes"], pd.DataFrame)


def test_critical_divergence_empty_dataframe():
    result = compute_critical_divergence(pd.DataFrame())
    assert isinstance(result["hot_takes"], pd.DataFrame)
    assert isinstance(result["hidden_dislikes"], pd.DataFrame)
    assert len(result["hot_takes"]) == 0
    assert len(result["hidden_dislikes"]) == 0


def test_critical_divergence_all_null_imdb_ratings():
    df = pd.DataFrame({
        "Title": ["A", "B"],
        "Your_Rating": [9.0, 3.0],
        "IMDb_Rating": [None, None],
    })
    result = compute_critical_divergence(df)
    assert len(result["hot_takes"]) == 0
    assert len(result["hidden_dislikes"]) == 0


# ---------------------------------------------------------------------------
# Integration: parse_imdb_csv output → analytics functions
# ---------------------------------------------------------------------------


def test_integration_parse_to_distribution(sample_csv_string):
    df = parse_imdb_csv(sample_csv_string)
    result = calculate_rating_distribution(df)
    assert len(result) == 10
    assert result["Count"].sum() == len(df)


def test_integration_parse_to_genre_breakdown(sample_csv_string):
    df = parse_imdb_csv(sample_csv_string)
    result = compute_genre_breakdown(df)
    assert isinstance(result, pd.DataFrame)
    assert "Genre" in result.columns


def test_integration_parse_to_divergence(sample_csv_string):
    df = parse_imdb_csv(sample_csv_string)
    result = compute_critical_divergence(df)
    assert "hot_takes" in result
    assert "hidden_dislikes" in result


# ---------------------------------------------------------------------------
# suggest_hidden_gems
# ---------------------------------------------------------------------------


def _make_gems_df(rows):
    """Helper: build a DataFrame from list of (title, your_rating, imdb_rating) tuples."""
    return pd.DataFrame(rows, columns=["Title", "Your_Rating", "IMDb_Rating"])


def test_hidden_gems_basic():
    df = _make_gems_df([
        ("Loved It", 9, 6.5),   # gem — high personal, low IMDb
        ("Mainstream", 9, 8.5), # not a gem — IMDb too high
        ("Disliked", 4, 5.0),   # not a gem — personal rating too low
    ])
    result = suggest_hidden_gems(df)
    assert len(result) == 1
    assert result["Title"].iloc[0] == "Loved It"


def test_hidden_gems_exact_boundary_included():
    df = _make_gems_df([("Edge", 8, 7.0)])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert len(result) == 1


def test_hidden_gems_just_outside_boundary_excluded():
    df = _make_gems_df([("Close", 7, 6.9)])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert len(result) == 0


def test_hidden_gems_sorted_by_your_rating_desc():
    df = _make_gems_df([
        ("B", 8, 5.0),
        ("A", 10, 4.0),
        ("C", 9, 6.0),
    ])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert list(result["Your_Rating"]) == [10, 9, 8]


def test_hidden_gems_tiebreak_by_imdb_rating_asc():
    df = _make_gems_df([
        ("High IMDb", 9, 6.5),
        ("Low IMDb", 9, 4.0),
    ])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert result["Title"].iloc[0] == "Low IMDb"


def test_hidden_gems_gap_column_present():
    df = _make_gems_df([("Film", 9, 5.0)])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert "Gap" in result.columns
    assert result["Gap"].iloc[0] == 4.0


def test_hidden_gems_null_imdb_rating_excluded():
    df = _make_gems_df([("No IMDb", 9, None), ("Has IMDb", 9, 5.0)])
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert len(result) == 1
    assert result["Title"].iloc[0] == "Has IMDb"


def test_hidden_gems_empty_dataframe():
    result = suggest_hidden_gems(pd.DataFrame())
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_hidden_gems_custom_thresholds():
    df = _make_gems_df([
        ("Super Niche", 10, 4.0),
        ("Pretty Good", 8, 6.5),
    ])
    # Tighter threshold — only absolute gems
    result = suggest_hidden_gems(df, min_user_rating=10, max_imdb_rating=5.0)
    assert len(result) == 1
    assert result["Title"].iloc[0] == "Super Niche"


def test_hidden_gems_integration(sample_csv_string):
    """parse_imdb_csv output feeds cleanly into suggest_hidden_gems."""
    from src.services.data_service import parse_imdb_csv
    df = parse_imdb_csv(sample_csv_string)
    result = suggest_hidden_gems(df, min_user_rating=8, max_imdb_rating=7.0)
    assert isinstance(result, pd.DataFrame)
    # All returned rows must satisfy the threshold criteria
    if not result.empty:
        assert (result["Your_Rating"] >= 8).all()
        assert (result["IMDb_Rating"] <= 7.0).all()
