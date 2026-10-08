# CineTrack Local
### Built entirely by AI — from spec to shipped, in a single conversation.

---

## The Premise

> *What happens when you give an AI agent a requirements document and say "build it"?*

This project is the answer.

**CineTrack Local** is a full-stack Python web application for analysing your IMDb movie ratings. It was planned, architected, coded, debugged, and shipped — every file, every test, every fix — through a live conversation with **IBM Bob**, an AI software engineering agent.

No starter template. No boilerplate. One spec document. One conversation.

---

## What Was Built

A local-first web application that:

- **Imports** your IMDb ratings via your profile URL or a direct CSV upload
- **Inspects and filters** your data with a live rating slider, title search, and column selector
- **Exports** the filtered view as UTF-8 CSV or a named Excel workbook
- **Analyses your taste** across three dashboards:
  - 📊 Rating distribution (bar chart, mean, median, total count)
  - 🎭 Genre affinity — your top 10 genres by volume and average score
  - ⚡ Critical divergence — films you rate wildly differently from the IMDb crowd

### Tech Stack

| Layer | Library | Version |
|---|---|---|
| UI | Streamlit | 1.38.0 |
| Data | pandas | 2.2.3 |
| Charts | Altair | 5.5.0 |
| Excel | openpyxl | 3.1.5 |
| HTTP | requests + BeautifulSoup4 | 2.32.3 / 4.12.3 |
| Tests | pytest | 8.3.2 |
| Runtime | Python | 3.13.16 |

---

## The Development Process

This is the part worth paying attention to.

### Step 1 — Spec In

A single markdown document ([`SPEC.md`](SPEC.md)) defined the full requirements:
5 features, a data model with 12 fields, exact function signatures, pinned dependency versions, the directory structure, error-handling philosophy, and testing requirements.

That document was handed to Bob with one instruction: *build it.*

### Step 2 — Planning

Bob read the spec, identified three ambiguities, asked clarifying questions, and produced a complete [`PLAN.md`](PLAN.md) — a structured build order covering:

- Every file to create, in dependency order
- The purpose and key functions of each
- 78 named test cases across unit, integration, functional, and E2E layers
- Exact commands to run the application and every test suite

**No code was written yet.** Planning came first.

### Step 3 — Build

Bob worked through 12 implementation tasks in sequence:

```
requirements.txt → __init__.py files → constants.py
→ imdb_service.py → data_service.py → analytics_service.py
→ app.py → conftest.py → test_imdb_service.py
→ test_data_service.py → test_analytics_service.py → test_e2e.py
```

Each service module was built independently and tested before the UI was touched. The Streamlit layer was the last thing written — and it contained zero business logic.

### Step 4 — Real-World Debugging

This is where it got interesting. When the code met reality, three things broke:

| Problem | Root Cause | Fix |
|---|---|---|
| `pandas==2.2.2` install failed | No pre-built wheel for Python 3.13 | Bumped to `2.2.3` |
| `altair==5.4.1` crashed on import | `TypedDict(closed=True)` not supported in Python 3.13 | Bumped to `5.5.0` |
| Test fixture caused `ParserError` | Multi-genre CSV values unquoted — pandas saw extra columns | Wrapped all comma-containing fields in quotes |

Bob diagnosed each failure from the traceback, identified the root cause, and applied the minimal fix — no unnecessary changes to surrounding code.

### Step 5 — Live Feature Iteration

After the app was running, requirements evolved through conversation:

**"The username format is not correct — my actual username is mrcolley."**
→ Bob discovered the spec assumed `ur\d+` numeric IDs only. Real IMDb IDs are alphanumeric and dotted (e.g. `p.xd2gqvhctziu3txmdxu7dzktoi`). The regex was rewritten and the tests updated to match reality.

**"I want it to redirect to the IMDb page and allow the user to login, then get the data."**
→ Bob implemented a session-cookie flow. When that failed (IMDb's AWS WAF CAPTCHA blocked all programmatic requests regardless of cookies), Bob diagnosed the real problem, scrapped the broken approach, and replaced it with a clean deep-link flow that guides the user through the manual export — the only path that actually works.

Each iteration left the test suite green.

---

## By The Numbers

| Metric | Value |
|---|---|
| Files created | 14 Python files + config |
| Lines of application code | ~650 |
| Lines of test code | ~620 |
| Test cases | 78 |
| Test pass rate | 100% |
| Conversation turns to first passing tests | ~15 |
| Bugs caught by tests | 3 |
| Real-world issues caught post-launch | 4 |

---

## What the AI Got Right

**Architecture first.** Bob separated concerns cleanly without being asked: a pure service layer (`imdb_service`, `data_service`, `analytics_service`) with zero Streamlit imports, and a thin UI layer that only calls those services. This made every service independently testable from day one.

**Honest about limitations.** When the IMDb WAF blocked all programmatic requests — a fact not in the spec — Bob ran a live diagnostic, read the response body, identified the 202 + AWS WAF CAPTCHA pattern, and told the truth: *"this cannot be made to work with requests."* It then proposed and built a better alternative.

**Tests as a safety net.** The 78-test suite caught three real bugs before the app was ever run: the CSV quoting issue, the regex over-matching, and the wrong assumption about IMDb ID format. Without tests, all three would have been silent data corruption or runtime crashes.

**Minimal changes.** Every fix touched exactly the lines that needed changing. No refactors, no cleanups, no "while I'm here" additions.

---

## What the AI Got Wrong (and How It Recovered)

**The spec assumed numeric IMDb IDs.** Bob faithfully implemented `^ur\d+$` validation as specified — but real IMDb IDs don't always match that pattern. The spec was wrong; Bob coded what it said. The fix required a real user to test it.

**The cookie approach was worth trying.** Implementing the `at-main` session cookie flow was a reasonable engineering attempt. It failed because IMDb's WAF operates below the HTTP layer — something only discoverable by actually sending the request and reading the response. Bob tried it, diagnosed the failure, and moved on cleanly.

**The lesson:** AI agents are excellent at implementing what's specified and diagnosing what's observable. They're limited by the quality of the spec and by information that only exists at runtime.

---

## Try It

```powershell
# Clone / navigate to the project
cd C:\Users\mrcol\my-spec-project

# Activate the environment
.venv\Scripts\Activate.ps1        # PowerShell
# or: .venv\Scripts\activate.bat  # CMD

# Run the app
python -m streamlit run app.py
# → http://localhost:8501

# Run the tests
.venv\Scripts\pytest.exe tests/ -v
# → 78 passed
```

---

## The Files

```
my-spec-project/
├── SPEC.md                         ← the only human input
├── PLAN.md                         ← AI-generated build plan
├── PRESENTATION.md                 ← this document
├── requirements.txt
├── app.py                          ← Streamlit UI
├── src/
│   ├── services/
│   │   ├── imdb_service.py         ← ID parsing, HTTP, BS4
│   │   ├── data_service.py         ← CSV parsing, filtering, Excel export
│   │   └── analytics_service.py    ← distribution, genres, divergence
│   └── utils/constants.py
└── tests/
    ├── conftest.py
    ├── test_imdb_service.py        ← 20 tests
    ├── test_data_service.py        ← 27 tests
    ├── test_analytics_service.py   ← 31 tests
    └── test_e2e.py                 ← 9 end-to-end tests
```

---

*Built with [IBM Bob](https://www.ibm.com/products/bob) · Python 3.13 · Streamlit 1.38*
