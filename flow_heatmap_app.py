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
    # --- Normalize and Rename ---
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
    # Normalize casing
    df["ticker"] = df["ticker"].astype(str).str.upper()
    # Standardize type
    df["type"] = df["type"].astype(str).str.lower().str.strip()
    df.loc[df["type"].str.contains("call"), "type"] = "call"
    df.loc[df["type"].str.contains("put"), "type"] = "put"
    df = df[df["type"].isin(["call", "put"])]
    # Standardize direction
    normalize_direction = {
        "bought": "buy",
        "buy": "buy",
        "purchased": "buy",
        "sold": "sell",
        "sell": "sell",
        "shorted": "sell"
    }
    df["direction"] = df["direction"].str.lower().map(normalize_direction).fillna(df["direction"])
    # Numeric
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

option_types = ["Call", "Put", "Both"]
actions = ["Buy", "Sell", "Both"]
selected_type = st.sidebar.radio("Option Type", option_types, horizontal=True)
selected_action = st.sidebar.radio("Action", actions, horizontal=True)

viz_mode = st.sidebar.radio(
    "Heatmap Mode",
    ["Buys", "Sells", "Net (Buys - Sells)"],
    index=0
)

cmap_choice = st.sidebar.selectbox(
    "Colormap",
    ["viridis", "rocket", "YlGnBu", "coolwarm", "vlag"],
    index=0
)

# --- FILTER FUNCTION ---

def filter_trades(df, ticker, option_type, action, direction_override=None):
    mask = df["ticker"] == ticker
    if option_type != "Both":
        mask = mask & (df["type"] == option_type.lower())
    if action != "Both":
        mask = mask & (df["direction"] == action.lower())
    if direction_override is not None:
        mask = mask & (df["direction"] == direction_override)
    # Drop NAs
    result = df[mask].dropna(subset=["strike", "expiry", "size"])
    return result

# --- DATA PREP FOR PIVOTS ---

def make_heatmap_data(trades_df):
    heatmap_data = trades_df.pivot_table(
        index="strike",
        columns="expiry",
        values="size",
        aggfunc="sum",
        fill_value=0
    )
    heatmap_data = heatmap_data.sort_index(axis=0)
    heatmap_data = heatmap_data[sorted(heatmap_data.columns, key=lambda x: (len(x), x))]
    return heatmap_data

# --- ALL FILTERING HERE ---

if viz_mode == "Net (Buys - Sells)":
    # Only relevant for call/put or both
    if selected_action != "Both":
        st.warning("For Net mode, 'Action' is forced to Both.")
    buy_trades = filter_trades(df, selected_ticker, selected_type, 'Both', direction_override="buy")
    sell_trades = filter_trades(df, selected_ticker, selected_type, 'Both', direction_override="sell")
    buy_hm = make_heatmap_data(buy_trades)
    sell_hm = make_heatmap_data(sell_trades)
    all_strikes = sorted(set(buy_hm.index).union(set(sell_hm.index)))
    all_expiries = sorted(set(buy_hm.columns).union(set(sell_hm.columns)), key=lambda x: (len(x), x))
    buy_hm = buy_hm.reindex(index=all_strikes, columns=all_expiries, fill_value=0)
    sell_hm = sell_hm.reindex(index=all_strikes, columns=all_expiries, fill_value=0)
    net_hm = buy_hm - sell_hm
    heatmap_data = net_hm
    title_sub = "Net (Buys minus Sells)"
else:
    trade_action = "buy" if viz_mode == "Buys" else "sell"
    filtered = filter_trades(df, selected_ticker, selected_type, selected_action if selected_action != "Both" else "Both")
    # In case they selected "Both" in sidebar, filter just for buys/sells if needed for this mode
    if selected_action == "Both":
        filtered = filtered[filtered["direction"] == trade_action]
    heatmap_data = make_heatmap_data(filtered)
    title_sub = trade_action.capitalize() + "s"

# --- VISUALIZATION ---

if heatmap_data.empty:
    st.warning("No matches. Try different trade type/filters.")
    st.stop()

if heatmap_data.shape[1] > 20:
    st.warning("Warning: More than 20 expiries! Reduce for cleaner heatmap.")

min_v, max_v = float(heatmap_data.min().min()), float(heatmap_data.max().max())
if viz_mode == "Net (Buys - Sells)":
    vmax = max(abs(min_v), abs(max_v))
    vmin = -vmax
else:
    vmin, vmax = 0, None

st.subheader(f"Trade Size Heatmap: {selected_ticker} | {selected_type} | {title_sub}")

fig, ax = plt.subplots(figsize=(2.2 + heatmap_data.shape[1], 6))
sns.heatmap(
    heatmap_data,
    cmap=cmap_choice,
    annot=True,
    fmt=".0f",
    linewidths=0.5,
    cbar=True,
    ax=ax,
    center=0 if viz_mode == "Net (Buys - Sells)" else None,
    vmin=vmin,
    vmax=vmax
)
ax.set_xlabel("Expiry")
ax.set_ylabel("Strike")
ax.set_title(f"Total size per strike-expiry")

plt.xticks(rotation=45, ha='right')
plt.tight_layout(pad=1.5)
st.pyplot(fig)

with st.expander("Show underlying data table"):
    st.dataframe(heatmap_data)

# --- OPTIONAL: Show Trade Table (raw) below ---
with st.expander("Show filtered trade list"):
    if viz_mode == "Net (Buys - Sells)":
        st.dataframe(pd.concat([
            buy_trades.assign(direction='buy'),
            sell_trades.assign(direction='sell')
        ]).sort_values(by=["expiry","strike","type", "direction"]))
    else:
        st.dataframe(filtered)

# --- OPTIONAL: Summary Stats ---
with st.expander("Summary stats"):
    # For buy/sell/Net
    st.write(f"Total contracts: {int(heatmap_data.values.sum())}")
    st.write(f"Strikes: {heatmap_data.shape[0]}; Expiries: {heatmap_data.shape[1]}")
    max_cell = heatmap_data.stack().idxmax() if not heatmap_data.empty else None
    if max_cell:
        st.write(f"Largest position: Strike {max_cell[0]}, Expiry {max_cell[1]}, Size {int(heatmap_data.loc[max_cell[0], max_cell[1]])}")

# --- Download Buttons ---

st.markdown("---")
st.markdown("### Download Filtered Data")

if viz_mode == "Net (Buys - Sells)":
    st.download_button(
        "Download Net Heatmap (CSV)",
        heatmap_data.reset_index().to_csv(index=False),
        file_name=f"net_heatmap_{selected_ticker}_{selected_type}.csv",
        mime="text/csv"
    )
    st.download_button(
        "Download Combined Trade List (CSV)",
        pd.concat([
            buy_trades.assign(direction="buy"),
            sell_trades.assign(direction="sell")
        ]).to_csv(index=False),
        file_name=f"all_trades_{selected_ticker}_{selected_type}.csv",
        mime="text/csv"
    )
else:
    st.download_button(
        "Download Heatmap (CSV)",
        heatmap_data.reset_index().to_csv(index=False),
        file_name=f"heatmap_{selected_ticker}_{selected_type}_{viz_mode.lower()}.csv",
        mime="text/csv"
    )
    st.download_button(
        "Download Trade List (CSV)",
        filtered.to_csv(index=False),
        file_name=f"trades_{selected_ticker}_{selected_type}_{viz_mode.lower()}.csv",
        mime="text/csv"
    )


# --- UI Hints and Docs ---

with st.expander("Help / About"):
    st.write("""
    - **Ticker**: Select asset (stock or ETF).
    - **Option Type**: Call, Put, or Both.
    - **Action**: Buys, Sells, or Both.
    - **Heatmap Mode**: Visualize Buys, Sells, or Net (Buys minus Sells).
    - **Colormap**: Change color style for heatmap.
    - **Net mode**: Highlights if a strike/expiry has more Buys (positive, e.g. blue) or Sells (negative, e.g. red).

    _Table and heatmap update dynamically._

    _Works with JSON trade dumps as described in your data pipeline._
    """)

# --- (End of file) ---
