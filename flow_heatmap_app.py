```File input: Pick (upload) the daily deduped JSON.
Ticker selector: Choose which ticker to visualize (from those in the file).
Trade filter: Maybe radio buttons/dropdowns for:
Calls bought
Puts sold
(maybe future: “all calls bought or puts sold”)
Heatmap plot: X = expiry, Y = strike, Cell = sum(size) (or count, but size preferred).```

#data file expectation:
```[
  {
    "ticker": "SPY",
    "type": "call",
    "direction": "buy",
    "expiry": "DEC30",
    "strike": 420,
    "size": 100,
    ...
  }
]```

# Need to check the LLM outputs here first


#All dedupes go in /deduped_trades/ and files are named like YYYYMMDD_deduped.json?





import streamlit as st
import pandas as pd
import os
import glob

# --- Step 1: Find latest deduped file in the given folder ---

@st.cache_data
def get_latest_deduped_json(folder="./deduped_trades"):
    """
    Finds the most recently-modified *_deduped.json file in the specified folder.
    Returns path to file.
    """
    file_list = glob.glob(os.path.join(folder, "*_deduped.json"))
    if not file_list:
        return None
    # Get most recently modified (or could use sorted by filename if filenames == dates)
    latest_file = max(file_list, key=os.path.getmtime)
    return latest_file

latest_file = get_latest_deduped_json()
if not latest_file:
    st.error(f"No deduped files found in ./deduped_trades/. Please run Step 4 first!")
    st.stop()
st.success(f"Loaded latest deduped file: {os.path.basename(latest_file)}")

@st.cache_data
def load_data(path):
    df = pd.read_json(path)
    return df

df = load_data(latest_file)



# --- Step 2: Sidebar controls ---

st.sidebar.header("Trade Filters")

# Get available tickers from data.
tickers = sorted(df["ticker"].dropna().unique().tolist())
selected_ticker = st.sidebar.selectbox("Select Ticker", tickers, index=0)

# Trade type filter: 'Calls bought', 'Puts sold', or 'Both'
trade_type = st.sidebar.radio(
    "Show:",
    [
        "Calls Bought",
        "Puts Sold",
        "Both (Calls Bought & Puts Sold)"
    ],
    index=0
)



# --- Step 3: Filter the DataFrame based on sidebar selections ---

if trade_type == "Calls Bought":
    filtered = df[
        (df["ticker"] == selected_ticker) &
        (df["type"].str.lower() == "call") &
        (df["direction"].str.lower().str.startswith("buy"))
    ]
elif trade_type == "Puts Sold":
    filtered = df[
        (df["ticker"] == selected_ticker) &
        (df["type"].str.lower() == "put") &
        (df["direction"].str.lower().str.startswith("sell"))
    ]
else:
    # Both — union of calls bought and puts sold
    filtered = df[
        (df["ticker"] == selected_ticker) &
        (
            ((df["type"].str.lower() == "call") & (df["direction"].str.lower().str.startswith("buy")))
            |
            ((df["type"].str.lower() == "put") & (df["direction"].str.lower().str.startswith("sell")))
        )
    ]

st.info(f"Found {len(filtered)} matching trades for {selected_ticker} ({trade_type})")

if filtered.empty:
    st.warning("No data for this combination! Try another ticker or filter.")
    st.stop()




import numpy as np

# --- Step 2A: Ensure strike and expiry columns are clean (if present) ---

# Remove trades missing either strike or expiry (since can't plot these)
matrix_df = filtered.dropna(subset=["strike", "expiry", "size"]).copy()

# Convert strikes to float (optional, for sort/order/heatmap axis)
matrix_df["strike"] = matrix_df["strike"].astype(float)

# Make expiry a string for axis labeling
matrix_df["expiry"] = matrix_df["expiry"].astype(str)

if matrix_df.empty:
    st.warning("No trades with both expiry and strike for this filter. Pick a new filter/ticker.")
    st.stop()

# --- Step 2B: Pivot table ("Heatmap data") ---

heatmap_data = matrix_df.pivot_table(
    index="strike",
    columns="expiry",
    values="size",
    aggfunc="sum",
    fill_value=0
)



import matplotlib.pyplot as plt
import seaborn as sns

st.subheader(f"Expiry × Strike Size Heatmap — {selected_ticker} ({trade_type})")

fig, ax = plt.subplots(figsize=(1.5 + heatmap_data.shape[1], 6))

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
ax.set_title(f"Total size traded ({trade_type}) per expiry-strike")
plt.xticks(rotation=45, ha='right')

st.pyplot(fig)



with st.expander("Show underlying data table"):
    st.dataframe(heatmap_data)
