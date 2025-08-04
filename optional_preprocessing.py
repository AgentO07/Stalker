from __future__ import annotations
import json, pathlib, re, unicodedata
from typing import List, Dict

# 1)  universe of tickers you care about  -------------------------------
TICKERS = [
    'SPY','QQQ','IWM','VIX','FXI','SPX','NDX','RTY',
    'AAPL','TSLA','NVDA','AMZN','AMD'
]

# Build a single case-insensitive regex:
# … match TICKER when it is not glued to other letters / digits (handles “.SPX” too)
_ticker_regex = re.compile(
    r'(?<![A-Z0-9.])(' + '|'.join(map(re.escape, TICKERS)) + r')(?![A-Z0-9])',
    flags=re.IGNORECASE
)

# 2)  helpers  ----------------------------------------------------------
def clean_text(txt: str) -> str:
    """Unicode-normalise, kill weird spaces, collapse runs of spaces/tabs."""
    txt = unicodedata.normalize("NFKC", txt).replace('\u00A0', ' ')
    txt = '\n'.join(re.sub(r'[ \t]+', ' ', line) for line in txt.splitlines())
    return txt.strip()

def find_tickers(txt: str) -> List[str]:
    """Return unique tickers (uppercase) that appear in txt."""
    return sorted({m.group(1).upper() for m in _ticker_regex.finditer(txt)})

# 3)  core routine  -----------------------------------------------------
def preprocess_file(in_path: pathlib.Path, out_path: pathlib.Path) -> None:
    """
    Read one *_structured.json file, keep only tagged messages,
    enrich them, and dump a flat list of dicts.
    """
    # --- load ----------------------------------------------------------
    data = json.loads(in_path.read_text(encoding='utf-8'))

    # the step-1 output may be either a wrapper {"messages":[…]} or a flat list
    messages: List[Dict] = data['messages'] if isinstance(data, dict) else data

    # --- enrich & filter ----------------------------------------------
    kept: List[Dict] = []
    for msg in messages:
        raw = msg.get('raw_text') or msg.get('text', '')
        cln = clean_text(raw)
        tags = find_tickers(cln)
        if not tags:                         # DROP messages w/o focus tickers
            continue

        new_msg = dict(msg)                  # shallow copy so we don’t mutate
        new_msg['clean_text'] = cln
        new_msg['tickers']    = tags         # plural list
        kept.append(new_msg)

    # --- dump ----------------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(kept, indent=2, ensure_ascii=False),
                        encoding='utf-8')
    print(f"{in_path.name:>35}  →  {len(kept):3d} msgs kept")

# 4)  batch driver  -----------------------------------------------------
def batch_preprocess(input_dir: str, output_dir: str):
    in_dir  = pathlib.Path(input_dir)
    out_dir = pathlib.Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob('*_structured.json'))
    print(f"Found {len(files)} structured files.")

    for fp in files:
        out_fp = out_dir / fp.name.replace('_structured.json', '_preproc.json')
        preprocess_file(fp, out_fp)

# ----------------------------------------------------------------------
if __name__ == '__main__':
    batch_preprocess('./structured', './preprocessed')
