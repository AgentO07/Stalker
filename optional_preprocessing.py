import json
import os
import re

# Add or modify to match your focus universe
TICKERS = ['SPY','QQQ','IWM','VIX','FXI','SPX','NDX','RTY','AAPL','TSLA','NVDA','AMZN','AMD','GOOG','GOOGL','AVGO','BAC','ASHR','TSLA','GLD','IBIT','USO','CVNA','EM','EEM','KWEB','RKT','ORCL','BA','MSFT','APLD','QUBT','RGTI','META','NVTS','CRWV','GME','RH','ADBE','MOS','JOBY','PEP','B'] # Expand as you like

def clean_text(text):
    """
    Normalize and tidy the message text.
    1. Convert to uppercase.
    2. Remove excessive spaces.
    3. Remove junk punctuation except for those commonly used in trade notation.
    """
    # Convert to uppercase for standardization and easier matching
    text = text.upper()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Optionally strip unwanted punctuation (here we keep . / % - $ , +)
    # Uncomment this line if you want a more strict cleaning: 
    # text = re.sub(r'[^\w\s\.\,\-\/\%\+\$]', '', text)
    return text.strip()

def tag_ticker(text):
    """
    Find the first matching ticker in the clean text.
    Returns the ticker (as appears in TICKERS) or None if not found.
    """
    for ticker in TICKERS:
        # Look for the ticker as a word or as a word boundary (to avoid partial matches)
        if re.search(rf'\b{re.escape(ticker)}\b', text):
            return ticker
    return None

def preprocess_structured_json(input_path, output_path):
    """
    Loads structured step-1 JSON; adds 'clean_text' and 'ticker' to each message.
    Outputs to output_path.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    for msg in messages:
        cln = clean_text(msg['raw_text'])
        tick = tag_ticker(cln)
        msg['clean_text'] = cln
        msg['ticker'] = tick

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    print(f"Preprocessed {input_path} -> {output_path} ({len(messages)} messages)")

def batch_preprocess_structured(input_folder, output_folder):
    """
    For all *_structured.json files in input_folder, create preproc jsons in output_folder.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    input_files = [f for f in os.listdir(input_folder) if f.endswith('_structured.json')]
    print(f"Found {len(input_files)} structured transcript files for preprocessing.")
    for fname in input_files:
        input_path = os.path.join(input_folder, fname)
        base_name = fname.replace('_structured.json', '') # Strip off _structured.json
        output_path = os.path.join(output_folder, f"{base_name}_preproc.json")
        preprocess_structured_json(input_path, output_path)

# Example usage
if __name__ == "__main__":
    batch_preprocess_structured('./structured', './preprocessed')