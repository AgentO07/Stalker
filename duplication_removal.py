import os
import json

# Define which fields to use in the deduplication hash.
# (Edit this list to add/remove fields if your flow changes.)
FINGERPRINT_FIELDS = ["ticker", "expiry", "strike", "type", "direction", "price"]

def make_trade_fingerprint(trade):
    """
    Given a dictionary of trade fields, builds a normalized string as the key for deduplication.
    - Lowercase
    - Missing/extra fields are handled
    - Price rounded to nearest $0.05
    """
    def norm(val):
        if val is None:
            return ''
        if isinstance(val, str):
            return val.strip().lower()
        return str(val).lower()
    # For price, if present, round to nearest 0.05
    price_val = trade.get("price")
    if price_val is not None:
        try:
            price_val = round(float(price_val) / 0.05) * 0.05
        except Exception:
            price_val = ''
    else:
        price_val = ''
    fp_values = []
    for field in FINGERPRINT_FIELDS:
        if field == "price":
            fp_values.append(str(price_val))
        else:
            fp_values.append(norm(trade.get(field)))
    return "|".join(fp_values)

def load_all_trades_from_folder(folder_path):
    """
    Loads all trades from all _llm.json files in the passed folder.
    Returns a flat list of trade dicts (ignores null ones).
    """
    all_trades = []
    for fname in os.listdir(folder_path):
        if fname.endswith('_llm.json'):
            with open(os.path.join(folder_path, fname), 'r', encoding='utf-8') as f:
                messages = json.load(f)
            for msg in messages:
                trade = msg.get("llm_structured")
                if trade:  # Only non-null results
                    all_trades.append(trade)
    print(f"Loaded {len(all_trades)} total parsed trades from {folder_path}.")
    return all_trades

def dedupe_trades(trade_list):
    """
    Given a list of trade dicts, deduplicate using fingerprinting.
    Keeps only the first occurrence of each unique trade.
    """
    seen = {}
    deduped = []
    for trade in trade_list:
        fp = make_trade_fingerprint(trade)
        if fp not in seen:
            seen[fp] = True
            deduped.append(trade)
    print(f"Deduped to {len(deduped)} unique trades.")
    return deduped

def dedupe_trades_for_day(in_folder, out_folder, date_str):
    """
    Runs dedup for all _llm.json files for the given date in in_folder.
    Writes deduped list to out_folder/[date_str]_deduped.json
    Example date_str: '20250729'
    """
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
    # Optionally, you could filter in_folder for just *_{date_str}_llm.json files for precision
    trades = load_all_trades_from_folder(in_folder)
    deduped = dedupe_trades(trades)
    out_path = os.path.join(out_folder, f"{date_str}_deduped.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"✅ Written deduped list to {out_path}")

if __name__ == "__main__":
    # EXAMPLE USAGE
    in_folder = "./llm_parsed"              # Your folder of llm outputs
    out_folder = "./deduped_trades"         # Where to write deduped results
    date_str = "20250729"                   # Put your desired date here, matches all trades for the day

    dedupe_trades_for_day(in_folder, out_folder, date_str)