
# Need to check the LLM outputs here first


#All dedupes go in /deduped_trades/ and files are named like YYYYMMDD_deduped.json?

import streamlit as st
import pandas as pd
import os
import glob
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- File Loading and Normalization ---

@st.cache_data
def get_latest_deduped_json(folder="./deduped_trades"):
    file_list = glob.glob(os.path.join(folder, "*_deduped.json"))
    if not file_list:
        return None
    return max(file_list, key=os.path.getmtime)

latest_file = get_latest_deduped_json()
if not latest_file:
    st.error("No deduped files found. Please run your pre-processing pipeline!")
    st.stop()
st.success(f"Loaded: {os.path.basename(latest_file)}")

@st.cache_data
def load_data(path):
    with open(path) as f:
        raw = json.load(f)
        filtered = [x for x in raw if isinstance(x, dict)]
    df = pd.DataFrame(filtered)
    # --- Rename and normalize ---
    rename = {
        "ticker": "ticker",
        "option_type": "type",
        "action": "direction",
        "expiry": "expiry",
        "strike_1": "strike",
        "quantity": "size"
    }
    for k, v in rename.items():
        if k in df.columns and v != k:
            df[v] = df[k]
    # Only keep relevant columns
    keep_cols = ["ticker", "type", "direction", "strike", "expiry", "size"]
    df = df[[c for c in keep_cols if c in df.columns]]
    # Drop rows missing anything critical
    df = df.dropna(subset=keep_cols)
    # Normalize casing
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["type"] = df["type"].astype(str).str.lower().str.strip()
    df.loc[df["type"].str.contains("call"), "type"] = "call"
    df.loc[df["type"].str.contains("put"), "type"] = "put"
    df = df[df["type"].isin(["call", "put"])]
    df["direction"] = df["direction"].astype(str).str.lower().str.strip()
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    df["size"] = pd.to_numeric(df["size"], errors="coerce")
    df["expiry"] = df["expiry"].astype(str).str.upper()
    df = df.dropna(subset=["strike", "size", "expiry"])
    return df

df = load_data(latest_file)

# --- SIDEBAR CONTROLS ---

st.sidebar.header("Trade Filters")
tickers = sorted(df["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Ticker", tickers, index=0)
trade_type = st.sidebar.radio(
    "Show Trades:",
    ["Calls Bought", "Puts Sold", "Both (Calls Bought & Puts Sold)"],
    index=0
)

# --- FILTER DATA (robust for "bought"/"sold") ---
if trade_type == "Calls Bought":
    query = (df["ticker"] == selected_ticker) & (df["type"] == "call") & (df["direction"].isin(["buy", "bought"]))
elif trade_type == "Puts Sold":
    query = (df["ticker"] == selected_ticker) & (df["type"] == "put") & (df["direction"].isin(["sell", "sold"]))
else:
    query = (df["ticker"] == selected_ticker) & (
        ((df["type"] == "call") & (df["direction"].isin(["buy", "bought"]))) |
        ((df["type"] == "put") & (df["direction"].isin(["sell", "sold"])))
    )

filtered = df[query].dropna(subset=["strike", "expiry", "size"])
if filtered.empty:
    st.warning("No matches. Try other ticker/filters.")
    st.stop()

# --- PIVOT TABLE FOR HEATMAP ---
heatmap_data = filtered.pivot_table(
    index="strike",
    columns="expiry",
    values="size",
    aggfunc="sum",
    fill_value=0
)
heatmap_data = heatmap_data.sort_index(axis=0)  # strikes numeric order
heatmap_data = heatmap_data[sorted(heatmap_data.columns, key=lambda x: (len(x), x))]  # expiry alphanumeric order

if heatmap_data.shape[1] > 20:
    st.warning("Warning: More than 20 expiries! Reduce for cleaner heatmap.")

# --- VISUALIZATION ---

st.subheader(f"Trade Size Heatmap: {selected_ticker} ({trade_type})")
fig, ax = plt.subplots(figsize=(1.8 + heatmap_data.shape[1], 6))
sns.heatmap(
    heatmap_data,
    cmap="viridis",
    annot=True,
    fmt=".0f",
    linewidths=0.5,
    cbar=True,
    ax=ax
)
ax.set_xlabel("Expiry")
ax.set_ylabel("Strike")
ax.set_title(f"Total size per strike-expiry")

plt.xticks(rotation=45, ha='right')
plt.tight_layout(pad=1.5)
st.pyplot(fig)

with st.expander("Show underlying data table"):
    st.dataframe(heatmap_data)



# You can put this below your current heatmap, or as a separate tab!

