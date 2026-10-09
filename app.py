# app.py
# CineTrack Local — Streamlit UI entry point.
# All data logic is delegated to the service layer; this file only handles presentation.

import io

import altair as alt
import pandas as pd
import streamlit as st

from src.services.analytics_service import (
    calculate_rating_distribution,
    compute_critical_divergence,
    compute_genre_breakdown,
    suggest_hidden_gems,
)
from src.services.data_service import export_to_excel_buffer, filter_ratings, parse_imdb_csv
from src.services.imdb_service import extract_user_id
from src.utils.constants import ALL_COLUMNS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CineTrack Local",
    page_icon="🎬",
    layout="wide",
)

# Mobile-friendly CSS — improves touch targets, prevents horizontal overflow,
# and makes charts/tables readable on small screens.
st.markdown(
    """
    <style>
    /* Prevent horizontal scrolling on small screens */
    .block-container { padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
    /* Larger touch targets for sliders and buttons */
    .stSlider > div { padding-top: 0.5rem; padding-bottom: 0.5rem; }
    .stButton > button, .stDownloadButton > button {
        width: 100%; min-height: 2.75rem; font-size: 1rem;
    }
    /* Readable table font on mobile */
    .stDataFrame { font-size: 0.85rem; }
    /* Tabs scroll horizontally on small screens */
    .stTabs [data-baseweb="tab-list"] { flex-wrap: nowrap; overflow-x: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "df" not in st.session_state:
    st.session_state["df"] = None

# ---------------------------------------------------------------------------
# Sidebar — Ingestion Panel
# ---------------------------------------------------------------------------

st.sidebar.title("🎬 CineTrack Local")
st.sidebar.markdown("Import your IMDb ratings to get started.")

st.sidebar.subheader("Option 1 — Download from IMDb")

user_id_input = st.sidebar.text_input(
    "Enter your IMDb user ID or paste your profile URL",
    placeholder="ur12345678 or https://www.imdb.com/user/...",
    key="user_id_input",
)

_user_id_preview = extract_user_id(user_id_input) if user_id_input.strip() else None

if _user_id_preview:
    # Link to the ratings page — the Export button is there once the user is logged in.
    # We do NOT link directly to /ratings/export because IMDb's WAF blocks that without
    # a real browser session, and the URL also receives a trailing slash that causes a 404.
    ratings_page = f"https://www.imdb.com/user/{_user_id_preview}/ratings"
    st.sidebar.markdown(
        f'[🎬 Open my IMDb ratings page]({ratings_page})',
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        "1. Click the link above to open your IMDb ratings page.  \n"
        "2. Log in if prompted.  \n"
        "3. Click the **Export** button (top-right of your ratings list).  \n"
        "4. Save the downloaded `ratings.csv` file.  \n"
        "5. Upload it using **Option 2** below."
    )
else:
    st.sidebar.caption(
        "Enter your user ID or profile URL above to generate a link to your ratings page."
    )

st.sidebar.divider()

st.sidebar.subheader("Option 2 — Upload CSV")
uploaded_file = st.sidebar.file_uploader(
    "Upload your IMDb ratings.csv export",
    type=["csv"],
    key="csv_uploader",
)

if uploaded_file is not None:
    try:
        raw_bytes = io.BytesIO(uploaded_file.read())
        st.session_state["df"] = parse_imdb_csv(raw_bytes)
        st.toast(
            f"✅ Loaded {len(st.session_state['df'])} ratings from {uploaded_file.name}.",
            icon="✅",
        )
    except ValueError as exc:
        st.toast(f"❌ {exc}", icon="❌")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

df: pd.DataFrame | None = st.session_state["df"]

if df is None:
    st.info(
        "👈 Import your ratings using the sidebar to get started. "
        "You can enter your IMDb user ID or upload a `ratings.csv` file."
    )
    st.stop()

tab_inspect, tab_analytics = st.tabs(["🔍 Inspect & Filter", "📊 Analytics Dashboard"])

# ---------------------------------------------------------------------------
# Tab 1 — Inspect & Filter
# ---------------------------------------------------------------------------

with tab_inspect:
    st.subheader("Filter your ratings")

    available_columns = [c for c in ALL_COLUMNS if c in df.columns]

    selected_columns = st.multiselect(
        "Columns to display",
        options=available_columns,
        default=available_columns,
        key="col_select",
    )

    rating_range = st.slider(
        "Rating range",
        min_value=1,
        max_value=10,
        value=(1, 10),
        step=1,
        key="rating_slider",
    )

    search_query = st.text_input(
        "Search by title",
        placeholder="e.g. Shawshank",
        key="title_search",
    )

    # Apply filters — all client-side, no network requests.
    filtered_df = filter_ratings(
        df,
        min_rating=rating_range[0],
        max_rating=rating_range[1],
        search_query=search_query,
        selected_columns=selected_columns if selected_columns else None,
    )

    st.caption(f"Showing **{len(filtered_df)}** of **{len(df)}** rated titles.")
    st.dataframe(filtered_df, use_container_width=True)

    # Export controls — stacked vertically so buttons are full-width on mobile.
    st.divider()
    st.download_button(
        label="⬇️ Export CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="cinetrack_export.csv",
        mime="text/csv",
        key="export_csv_btn",
        use_container_width=True,
    )
    excel_buffer = export_to_excel_buffer(filtered_df)
    st.download_button(
        label="⬇️ Export Excel",
        data=excel_buffer,
        file_name="cinetrack_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_xlsx_btn",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Tab 2 — Analytics Dashboard
# ---------------------------------------------------------------------------

with tab_analytics:
    # Analytics operate on the currently filtered DataFrame so they honour
    # the active filter state (SPEC §5 AC4).
    analytics_df = filter_ratings(
        df,
        min_rating=rating_range[0],
        max_rating=rating_range[1],
        search_query=search_query,
    )

    st.subheader("📈 Rating Distribution")

    dist_df = calculate_rating_distribution(analytics_df)

    mean_rating = (
        round(analytics_df["Your_Rating"].dropna().astype(float).mean(), 2)
        if "Your_Rating" in analytics_df.columns and not analytics_df.empty
        else 0.0
    )
    median_rating = (
        analytics_df["Your_Rating"].dropna().astype(float).median()
        if "Your_Rating" in analytics_df.columns and not analytics_df.empty
        else 0.0
    )
    total_rated = len(analytics_df)

    m1, m2, m3 = st.columns(3)
    m1.metric("Mean Rating", f"{mean_rating:.2f}")
    m2.metric("Median Rating", f"{median_rating:.1f}")
    m3.metric("Total Rated", total_rated)

    dist_chart = (
        alt.Chart(dist_df)
        .mark_bar()
        .encode(
            x=alt.X("Rating:O", title="Your Rating", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Count:Q", title="Number of Titles"),
            tooltip=["Rating", "Count"],
        )
        .properties(height=300)
    )
    st.altair_chart(dist_chart, use_container_width=True)

    st.divider()
    st.subheader("🎭 Genre Affinity (Top 10)")

    genre_df = compute_genre_breakdown(analytics_df, top_n=10)

    if genre_df.empty:
        st.info("No genre data available for the current filter selection.")
    else:
        genre_chart = (
            alt.Chart(genre_df)
            .mark_bar()
            .encode(
                x=alt.X("title_count:Q", title="Number of Titles"),
                y=alt.Y(
                    "Genre:N",
                    sort="-x",
                    title="Genre",
                ),
                color=alt.Color("avg_user_rating:Q", scale=alt.Scale(scheme="blues")),
                tooltip=["Genre", "title_count", "avg_user_rating"],
            )
            .properties(height=350)
        )
        st.altair_chart(genre_chart, use_container_width=True)

    st.divider()
    st.subheader("⚡ Critical Divergence Matrix")
    st.caption(
        "Titles where your rating diverges from the IMDb community score by ±2.0 or more."
    )

    divergence = compute_critical_divergence(analytics_df)

    st.markdown("**🔥 Overrated by You** *(Your Rating − IMDb ≥ +2.0)*")
    hot = divergence["hot_takes"]
    if hot.empty:
        st.info("No titles where you rate significantly higher than IMDb.")
    else:
        display_cols = [c for c in ["Title", "Your_Rating", "IMDb_Rating", "Delta"] if c in hot.columns]
        st.dataframe(hot[display_cols], use_container_width=True)

    st.markdown("**🧊 Underrated by You** *(IMDb − Your Rating ≥ +2.0)*")
    cold = divergence["hidden_dislikes"]
    if cold.empty:
        st.info("No titles where IMDb rates significantly higher than you.")
    else:
        display_cols = [c for c in ["Title", "Your_Rating", "IMDb_Rating", "Delta"] if c in cold.columns]
        st.dataframe(cold[display_cols], use_container_width=True)

    st.divider()
    st.subheader("🌟 Your Hidden Gems")
    st.caption(
        "Films you rated **8 or higher** that IMDb rates **7.0 or below** — "
        "your personal favourites the world hasn't discovered yet."
    )

    min_user_rating = st.slider(
        "Minimum your rating", min_value=1, max_value=10, value=8, key="gem_min"
    )
    max_imdb_rating = st.slider(
        "Maximum IMDb rating", min_value=1.0, max_value=10.0, value=7.0,
        step=0.5, key="gem_max"
    )

    gems = suggest_hidden_gems(
        analytics_df,
        min_user_rating=min_user_rating,
        max_imdb_rating=max_imdb_rating,
    )

    if gems.empty:
        st.info(
            "No hidden gems found for the current settings. "
            "Try lowering the IMDb rating threshold or the minimum personal rating."
        )
    else:
        st.success(f"Found **{len(gems)}** hidden gem{'s' if len(gems) != 1 else ''}! 💎")
        display_cols = [c for c in ["Title", "Year", "Your_Rating", "IMDb_Rating", "Gap", "Genres"] if c in gems.columns]
        st.dataframe(gems[display_cols], use_container_width=True)
