import os
import json
import openai



## TO BE PROMPT ENGINEERED
# 1. Static instruction for LLM prompt (keeps you consistent for every call)
STATIC_INSTRUCTION = (
    "For each of the following messages, extract structured option/stock trade data if any is present. Your output should be a JSON array, with either a dictionary of trade info or null for each message. Each dictionary should include possible keys like: ticker, direction, type, expiry, strike, size, price.DO NOT output anything except a SINGLE JSON array of length N. No explanations, no markdown code blocks."
)



def build_batch_prompt(messages, use_clean_text=True):
    numbered_msgs = []
    for i, msg in enumerate(messages):
        txt = msg.get('clean_text') if use_clean_text and msg.get('clean_text') else msg.get('raw_text','')
        numbered_msgs.append(f"Message {i+1}: {txt}")
    return STATIC_INSTRUCTION + "\n\n" + "\n".join(numbered_msgs)


## OPTIONAL IF YOU WANT TO USE CLEAN TEXT OR THE RAW TEXT FROM EARLIER
# FLAGS TRUE AND FALSE
## false for raw input


# 2. Compose big prompt from the full file




def build_full_prompt(messages, use_clean_text=True):
    numbered_msgs = []
    for i, msg in enumerate(messages):
        txt = msg.get('clean_text') if use_clean_text and msg.get('clean_text') else msg.get('raw_text','')
        numbered_msgs.append(f"Message {i+1}: {txt}")
    return STATIC_INSTRUCTION + "\n\n" + "\n".join(numbered_msgs)


# Utility: batched
def batched(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


## MODEL TO BE CHANGED LATER, TOKEN SIZE TO BE INCREASED

# 3. Core function to process the whole file in a single LLM call
def llm_parse_full_file_batched(input_path, output_path, client, openai_model="gpt-3.5-turbo", use_clean_text=True, temperature=0, batch_size=40, max_tokens=2000):
    with open(input_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    all_structured = []
    n_messages = len(messages)
    for i, batch in enumerate(batched(messages, batch_size)):
        prompt = build_batch_prompt(batch, use_clean_text=use_clean_text)
        try:
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            llm_output = response.choices[0].message.content
            start = llm_output.find('[')
            stop = llm_output.rfind(']')
            json_text = llm_output[start:stop+1]
            trades = json.loads(json_text)
            if not isinstance(trades, list) or len(trades) != len(batch):
                raise Exception("LLM response length mismatch or not an array.")
        except Exception as e:
            print(f"Error in OpenAI call for {input_path} (batch {i+1}/{(n_messages+batch_size-1)//batch_size}):", e)
            trades = [None] * len(batch)

        # Pair timestamps with LLM result for just this batch
        for m, t in zip(batch, trades):
            all_structured.append({"timestamp": m["timestamp"], "llm_structured": t})

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_structured, f, indent=2, ensure_ascii=False)

    print(f"✅ Parsed: {input_path} => {output_path} ({len(all_structured)} messages)")



# 4. process all files in a folder
def llm_parse_all_files(input_folder, output_folder, client, use_clean_text=True, openai_model="gpt-3.5-turbo-16k", temperature=0, batch_size=40, max_tokens=2000):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    print(f"\nFound {len(files)} input files in {input_folder}\n")

    for fname in files:
        inpath = os.path.join(input_folder, fname)
        base = fname.replace('_preproc.json','').replace('_structured.json','')
        outpath = os.path.join(output_folder, base + "_llm.json")
        llm_parse_full_file_batched(
            inpath,
            outpath,
            client=client,
            openai_model=openai_model,
            use_clean_text=use_clean_text,
            temperature=temperature,
            batch_size=batch_size,
            max_tokens=max_tokens
        )
# -- Example usage (uncomment next lines to process everything in '/preprocessed') --
# llm_parse_all_files('./preprocessed', './llm_parsed', use_clean_text=True, model="gpt-3.5-turbo-16k", max_tokens=12000)


#################################################################################################################

'''Set your OpenAI API key in the script (openai.api_key = "YOUR_KEY").'''

##################################################################################################################



if __name__ == "__main__":
    # Put your OpenAI API key here
    
    client = openai.OpenAI(api_key="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")

    # Configuration
    input_folder = './preprocessed'     # or './structured'
    output_folder = './llm_parsed'
    use_clean_text = True
    openai_model = "gpt-4o"  # You can use chanfe
    temperature = 0
    batch_size = 25
    max_tokens = 2400

    llm_parse_all_files(
        input_folder=input_folder,
        output_folder=output_folder,
        client=client,
        use_clean_text=use_clean_text,
        openai_model=openai_model,
        temperature=temperature,
        batch_size=batch_size,
        max_tokens=max_tokens
    )