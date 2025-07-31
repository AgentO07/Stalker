import os
import json
import openai




## TO BE PROMPT ENGINEERED
# 1. Static instruction for LLM prompt (keeps you consistent for every call)
STATIC_INSTRUCTION = (
    "For each of the following messages, extract structured option/stock trade data if any is present. "
    "Your output should be a JSON array, with either a dictionary of trade info or null for each message. "
    "Each dictionary should include possible keys like: ticker, direction, type, expiry, strike, size, price."
)



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



## MODEL TO BE CHANGED LATER, TOKEN SIZE TO BE INCREASED

# 3. Core function to process the whole file in a single LLM call
def llm_parse_full_file(input_path, output_path, openai_model="gpt-3.5-turbo", use_clean_text=True, temperature=0, max_tokens=8000):
    with open(input_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    prompt = build_full_prompt(messages, use_clean_text)
    
    try:
        response = openai.ChatCompletion.create(
            model=openai_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        llm_output = response['choices'][0]['message']['content']
        start = llm_output.find('[')
        stop = llm_output.rfind(']')
        json_text = llm_output[start:stop+1]
        trades = json.loads(json_text)
    except Exception as e:
        print(f"Error in OpenAI call for {input_path}:", e)
        trades = [None] * len(messages)

    out = [
        {"timestamp": m["timestamp"], "llm_structured": t}
        for m, t in zip(messages, trades)
    ]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"✅ Parsed: {input_path} => {output_path} ({len(out)} messages)")




# 4. process all files in a folder
def llm_parse_all_files(input_folder, output_folder, use_clean_text=True, model="gpt-3.5-turbo-16k", temperature=0, max_tokens=12000):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    print(f"\nFound {len(files)} input files in {input_folder}\n")

    for fname in files:
        inpath = os.path.join(input_folder, fname)
        base = fname.replace('_preproc.json','').replace('_structured.json','')
        outpath = os.path.join(output_folder, base + "_llm.json")
        llm_parse_full_file(
            inpath,
            outpath,
            openai_model=model,
            use_clean_text=use_clean_text,
            temperature=temperature,
            max_tokens=max_tokens
        )
# -- Example usage (uncomment next lines to process everything in '/preprocessed') --
# openai.api_key = "YOUR_OPENAI_API_KEY"
# llm_parse_all_files('./preprocessed', './llm_parsed', use_clean_text=True, model="gpt-3.5-turbo-16k", max_tokens=12000)


#################################################################################################################

'''Set your OpenAI API key in the script (openai.api_key = "YOUR_KEY").'''

##################################################################################################################


if __name__ == "__main__":
    openai.api_key = "YOUR_OPENAI_API_KEY"
    # Change these paths if needed:
    input_folder = './preprocessed'      # or './structured' if not using preproc
    output_folder = './llm_parsed'
    use_clean_text = True                # Set to False if using structured/raw only
    model = "gpt-3.5-turbo-16k"          # 16k recommended for big files
    temperature = 0
    max_tokens = 12000                   # Increase if your messages are very long

    llm_parse_all_files(
        input_folder=input_folder,
        output_folder=output_folder,
        use_clean_text=use_clean_text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )