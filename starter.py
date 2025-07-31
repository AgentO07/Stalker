import re
import os
import json

def ingest_and_structure(input_path, output_path):
    """
    Convert a raw transcript text file into a structured JSON list (timestamp/message per block).
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    timestamped_msgs = []
    curr_message = {"timestamp": None, "raw_text": ""}
    timestamp_re = re.compile(r'^(\d{2}:\d{2}:\d{2})')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            curr_message["raw_text"] += '\n'
            continue

        match = timestamp_re.match(stripped)
        if match:
            if curr_message["raw_text"].strip() != "" or curr_message["timestamp"] is not None:
                timestamped_msgs.append(curr_message)
            curr_message = {
                "timestamp": match.group(1),
                "raw_text": stripped[len(match.group(1)):].strip()
            }
        else:
            if curr_message["raw_text"]:
                curr_message["raw_text"] += "\n"
            curr_message["raw_text"] += stripped

    if curr_message["raw_text"].strip() != "" or curr_message["timestamp"] is not None:
        timestamped_msgs.append(curr_message)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(timestamped_msgs, f, indent=2, ensure_ascii=False)

    print(f"Processed {input_path} with {len(timestamped_msgs)} messages.")

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