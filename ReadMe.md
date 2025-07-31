
---

## 📚 Table of Contents

1. [What Is This?](#what-is-this)
2. [Folder Structure](#folder-structure)
3. [Requirements](#requirements)
4. [How To Use](#how-to-use)
    - [Step 1: Ingest & Structure](#step-1-ingest--structure)
    - [Step 2: Optional Preprocessing](#step-2-optional-preprocessing)
    - [Step 3: LLM Parsing](#step-3-llm-parsing)
    - [Step 4: Deduplication of Trades](#step-4-deduplication-of-trades)
    - [Step 5: Dashboard & Analytics (Streamlit)](#step-5-dashboard--analytics-streamlit)
5. [Design Notes](#design-notes)
6. [FAQ / Customization](#faq--customization)

---

## What is this?

**A pipeline for option/ETF trade flow transcripts** (from brokers) that:

- **Parses raw text files** (chat logs, emails, etc.)
- **Optionally normalizes and tags instruments**
- **Uses LLM (OpenAI) to extract structured trade details**
- **Deduplicates “echoed” trades across brokers**
- **Lets you analyze and visualize the day’s unique trades without a complex database**

> Built for quant/PM flow desks, but easily modifiable for any broker transcript use-case.

---

## Folder Structure



stalker/
│
├── transcripts/          # Raw broker text files. (Input)
├── structured/           # Step 1 outputs: JSON messages per file.
├── preprocessed/         # Step 2 outputs: (optional) cleaned, tagged messages.
├── llm_parsed/           # Step 3 outputs: each message now has LLM-structured trade dict.
├── deduped_trades/       # Step 4: Unique, deduped trades for the day.
├── dashboard/            # Step 5: Streamlit dashboard code, etc.
│
├── step1_starter.py
├── step2_optional_preprocessing.py
├── step3_llm_parser.py # additional LLM_Batching (not needed for now).py
├── step4_duplication_removal.py
├── dashboard_app.py      # (later)
│
├── README.md
├── requirements.txt




---

## Requirements

- **Python 3.8+**
- `pandas`
- `streamlit`
- `openai` *(set your API key as env var or in code)*
- `tqdm` *(for progress, optional)*
- (maybe) `yfinance` or others if you expand analytics

Install everything at once:

'''pip install pandas streamlit openai tqdm





How to Use
Step 1: Ingest & Structure
Place all daily txt transcripts in /transcripts/ (named, e.g., citadel_20240731.txt).

Run:

python step1_starter.py
Produces /structured/[basename]_structured.json for each input.
Step 2: Optional Preprocessing
Improves LLM parsing by normalizing/capitalizing/tagging tickers.

Run:

python step2_optional_preprocessing.py
Produces /preprocessed/[basename]_preproc.json.
Can skip this—LLM will use raw text if you like.
Step 3: LLM Parsing
For each day, turns all messages in each file into LLM-extracted trade dicts.

Make sure your openai.api_key is set.

Run:

python step3_llm_parser.py
Reads from /preprocessed (default) or /structured
Outputs /llm_parsed/[basename]_llm.json
Step 4: Deduplication of Trades
Merge all LLM-structured outputs for the same day, dedupe repeated trades.

Run:

python step4_duplication_removal.py
Outputs /deduped_trades/YYYYMMDD_deduped.json
Step 5: Dashboard & Analytics (Streamlit)
Coming soon/see dashboard_app.py!

Visualize, filter, and analyze trades for each day’s deduped JSON.

