import re
import os
import json

TS_REGEX = re.compile(
    r'^(?P<ts>\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?)\s*(?P<body>.*)'
)

def ingest_and_structure(input_path: str | pathlib.Path,
                         output_path: str | pathlib.Path) -> list[dict]:
    """
    Parse a broker transcript into
        {
          "broker": "BRIAN CONNORS",
          "messages": [
              {"timestamp": "...", "text": "..."},
              ...
          ]
        }
    and dump as JSON.
    """
    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)

    with input_path.open(encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()

    # --- 1. broker / header --------------------------------------------------
    broker = lines[0].strip()           # first line = broker name
    start_idx = 1                       # start looking for timestamps here

    # If the first line is NOT a timestamp but NOT a name either
    # (e.g. "*** CHAT STARTED ***"), advance until we hit a timestamp.
    if TS_REGEX.match(broker):
        # actually the file has no broker name, rewind
        broker = None
        start_idx = 0

    # --- 2. iterate ----------------------------------------------------------
    messages, curr = [], {"timestamp": None, "text": ""}

    for raw in lines[start_idx:]:
        line = raw.rstrip('\n')
        m = TS_REGEX.match(line)

        if m:  # new message starts ------------------------------------------
            if curr["timestamp"] is not None or curr["text"].strip():
                messages.append(curr)
            curr = {
                "timestamp": m.group('ts'),
                "text": m.group('body').rstrip()
            }
        else:  # continuation line -------------------------------------------
            if curr["text"]:
                curr["text"] += '\n'
            curr["text"] += line

    if curr["timestamp"] is not None or curr["text"].strip():
        messages.append(curr)

    # --- 3. dump -------------------------------------------------------------
    wrapper = {"broker": broker, "messages": messages}
    output_path.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False),
                           encoding='utf-8')
    print(f"{input_path.name:>35}  →  {len(messages):3d} msgs")

    return wrapper

def batch_ingest_transcripts(input_folder, output_folder):
    """
    Process all .txt transcripts in input_folder and output corresponding structured JSON files in output_folder.
    """
    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # List input .txt files
    input_files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
    print(f"Found {len(input_files)} transcript files.")

    for fname in input_files:
        input_path = os.path.join(input_folder, fname)
        # e.g., 'citsec_transcript_202507.txt' -> 'citsec_transcript_202507_structured.json'
        base_name = os.path.splitext(fname)[0]  # removes .txt
        output_path = os.path.join(output_folder, f"{base_name}_structured.json")
        ingest_and_structure(input_path, output_path)

# Example usage:
if __name__ == "__main__":
    batch_ingest_transcripts('./transcripts', './structured')
