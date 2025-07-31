import openai
import json
import os
from tqdm import tqdm


#Prompt for LLm, can be changed
def make_prompt(messages, use_clean_text):
    """
    Given a list of message dicts, prepares a single prompt as a list of (user) messages for a batch call.
    If use_clean_text and 'clean_text' exists, use that. Else, use 'raw_text'.
    The prompt asks the LLM to extract structured trade data for every message.
    """
    prompt_messages = []
    for i, msg in enumerate(messages):
        msg_text = msg.get('clean_text') if use_clean_text and msg.get('clean_text') else msg.get('raw_text', '')
        prompt_messages.append(
            f"Message {i+1}: {msg_text}"
        )
    # Each message is in 'Message i: <text>' format so LLM can split output later.
    
    # Compile prompt: ask for list of JSON objects (or null) in order
    prompt = (
        "For each of the following messages, extract structured option/stock trade data if any is present. "
        "Your output should be a JSON array, with either a dictionary of trade info or null for each message. "
        "Each dictionary should include possible keys like: ticker, direction, type, expiry, strike, size, price.\n\n"
        + "\n".join(prompt_messages)
    )
    return prompt


# batching, dont think it will be able to handle all in one go
# also add a prompt on ONLY look for things from the text and not make shit up

def batch_list(lst, batch_size):
    """
    Utility: Splits a list into batches of at most batch_size.
    """
    for i in range(0, len(lst), batch_size):
        yield lst[i:i+batch_size]


def llm_parse_messages(input_path, output_path, openai_model="gpt-3.5-turbo", batch_size=50, use_clean_text=True):
    """
    Loads structured/preprocessed JSON from input_path, runs OpenAI LLM in batches.
    Each message's output is: {'timestamp':..., 'llm_structured':...}.
    Writes a JSON list to output_path.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    # Setup output container
    outputs = []

    for batch in tqdm(list(batch_list(messages, batch_size)), desc="LLM Batches"):
        prompt = make_prompt(batch, use_clean_text)
        # OpenAI ChatCompletion call, using single prompt for the batch (system role default is fine)
        try:
            response = openai.ChatCompletion.create(
                model=openai_model,
                messages=[
                    # System role helps, but user prompt is the real detailed "do this"
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0,
                response_format={"type": "json_object"}  # Ensures JSON response if using recent API
            )
            reply = response['choices'][0]['message']['content']
            # Parse response: must be a JSON array (one dict OR null for each message)
            # Remove possible preamble text, then extract JSON area
            first_bracket = reply.find('[')
            last_bracket = reply.rfind(']')
            json_str = reply[first_bracket:last_bracket+1]
            batch_results = json.loads(json_str)
            assert isinstance(batch_results, list), "OpenAI output was not a JSON array."
        except Exception as e:
            print(f"Error in LLM batch: {e}")  # Real code could do retries or log
            batch_results = [None] * len(batch)  # mark all as failed/null

        # For each item in batch, return just timestamp + llm_structured
        for msg, trade_struct in zip(batch, batch_results):
            outputs.append({
                "timestamp": msg["timestamp"],
                "llm_structured": trade_struct
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)

    print(f"LLM-parsed {input_path} => {len(outputs)} messages written to {output_path}")




#this is to automate over a folder 
# model to be changed

def batch_llm_parse(input_folder, output_folder, batch_size=50, use_clean_text=True, model="gpt-3.5-turbo"):
    """
    Runs llm_parse_messages for every json file in input_folder, puts result in output_folder.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Accepts both _preproc.json and _structured.json files for input
    input_files = [f for f in os.listdir(input_folder) if f.endswith('.json')]
    print(f"Found {len(input_files)} input files.")

    for fname in input_files:
        in_path = os.path.join(input_folder, fname)
        base = fname.replace('_preproc.json','').replace('_structured.json','')
        out_path = os.path.join(output_folder, base + "_llm.json")
        llm_parse_messages(
            in_path,
            out_path,
            openai_model=model,
            batch_size=batch_size,
            use_clean_text=use_clean_text
        )


#Optional: How to Run for All Your Data

if __name__ == "__main__":
    # Use '/preprocessed' as default, with clean text
    batch_llm_parse('./preprocessed', './llm_parsed', batch_size=50, use_clean_text=True)
    # If you want to run on raw messages:
    # batch_llm_parse('./structured', './llm_parsed', batch_size=50, use_clean_text=False)






###Place your OpenAI API key in your environment, or set openai.api_key = "YOUR_KEY" at the top of the script.
##Run script; processed files land in /llm_parsed.
#Inspect outputs, test how well prompt works; tweak if you want!