import os
import json

# === SETTINGS ===
PROVIDER = "gemini"  # "gemini" or "openai"
MODE = "roast"       # "roast" or "professional"

# === GEMINI SETUP ===
if PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key="AIzaSyBEBgM92yA43Xq0TtYoJpQz76qGipN63fU")
    model = genai.GenerativeModel("gemini-2.5-pro")

# === OPENAI SETUP (optional) ===
elif PROVIDER == "openai":
    from openai import OpenAI
    client = OpenAI(api_key="YOUR_OPENAI_KEY")

# Directory where your JSON responses are stored
response_dir = "./responses"

# Collect and merge entries
all_entries = []
for filename in os.listdir(response_dir):
    if filename.endswith(".json"):
        path = os.path.join(response_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            try:
                content = json.load(f)
                data = content.get("data")
                if content.get("success") and data:
                    if isinstance(data, list):
                        all_entries.extend(data)
                    elif isinstance(data, dict):
                        all_entries.append(data)
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON file: {filename}")

print(f"✅ Loaded {len(all_entries)} entries from {response_dir}")

# Flatten into one text input
input_text = ""
for idx, entry in enumerate(all_entries, start=1):
    table = entry.get("table", {})
    paras = entry.get("paras", [])
    input_text += f"\n--- ENTRY {idx} ---\n"
    input_text += "TABLE:\n" + json.dumps(table, indent=2) + "\n"
    if paras:
        input_text += "PARAGRAPHS:\n" + "\n".join(paras) + "\n"
    input_text += "\n" + "="*50 + "\n"

# Instruction based on mode
if MODE == "professional":
    style_instruction = """
    You are an expert behavioral psychologist and profiler.
    Consolidate all entries into one clear structured profile.
    Sections:
      1. Behavioral Traits
      2. Psychological Traits
      3. Character Assessment
      4. Lifestyle & Interests
      5. Sexual Orientation
      6. Emotions & Emotional State
      7. Religion & Politics
      8. Risks & Concerns
      9. Likely Motivations & Goals
    Write in a structured, professional tone.
    """
else:
    style_instruction = """
    You are a savage roastmaster disguised as a psychologist.
    Consolidate all entries into a roast profile.
    Sections:
      1. Behavioral Roasts
      2. Psychological Roasts
      3. Character Roasts
      4. Lifestyle & Interests
      5. Sexual Orientation Roast
      6. Emotional Roast
      7. Religion & Politics Roast
      8. Risks & Concerns
      9. Motivations & Goals
    Be witty, sarcastic, and playful.
    """

prompt = f"""
{style_instruction}

Here is the raw data:

{input_text}
"""

profile = ""

# === Run on Gemini ===
if PROVIDER == "gemini":
    response = model.generate_content(prompt)
    print("DEBUG RAW RESPONSE:", response)  # 🔍 Debug

    if hasattr(response, "text") and response.text:
        profile = response.text
    elif hasattr(response, "candidates") and response.candidates:
        parts = response.candidates[0].content.parts
        profile = "\n".join([p.text for p in parts if hasattr(p, "text")])
    else:
        profile = "⚠️ No text output from Gemini response."

# === Run on OpenAI ===
elif PROVIDER == "openai":
    chat_response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a psychologist and analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    if chat_response.choices:
        profile = chat_response.choices[0].message.content
    else:
        profile = "⚠️ No text output from OpenAI response."

# Save & print
print(f"\n=== CONSOLIDATED PROFILE ({MODE.upper()} - {PROVIDER.upper()}) ===\n")
print(profile)

with open(f"profile_{MODE}_{PROVIDER}.txt", "w", encoding="utf-8") as f:
    f.write(profile)

print(f"\n✅ Profile saved to profile_{MODE}_{PROVIDER}.txt")
