# CineTrack Local

A local-first web application for importing, inspecting, and analysing your IMDb movie ratings.

## Features

- **Import** ratings via your IMDb profile URL or by uploading a `ratings.csv` export directly.
- **Inspect & Filter** your data with a rating range slider, title search, and column selector.
- **Export** the filtered view as a UTF-8 CSV or a named Excel worksheet.
- **Analytics Dashboard** — four sections:
  - 📊 Rating distribution, mean, median, total count
  - 🎭 Genre affinity — top 10 genres by volume and average score
  - ⚡ Critical divergence — films you rate wildly differently from IMDb
  - 🌟 Hidden gems — films you loved that the world underrated (tunable thresholds)

---

## Requirements

- Python 3.13.x
- All dependencies listed in `requirements.txt`

---

## Setup

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Run the Application

```bash
streamlit run app.py
# Then open http://localhost:8501
```

---

## Run Tests

```bash
# Unit + integration tests
pytest tests/test_imdb_service.py tests/test_data_service.py tests/test_analytics_service.py -v

# End-to-end tests
pytest tests/test_e2e.py -v

# All tests
pytest tests/ -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Project Structure

```
cinetrack-local/
├── requirements.txt
├── README.md
├── app.py                          # Streamlit UI entry point
├── src/
│   ├── services/
│   │   ├── imdb_service.py         # Network ingestion & ID validation
│   │   ├── data_service.py         # Parsing, filtering, export
│   │   └── analytics_service.py    # Taste profile & analytics
│   └── utils/
│       └── constants.py            # Shared constants
└── tests/
    ├── conftest.py                 # Shared fixtures
    ├── test_imdb_service.py
    ├── test_data_service.py
    ├── test_analytics_service.py
    └── test_e2e.py
```
