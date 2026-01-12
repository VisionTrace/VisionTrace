import os
import json
import re

# --- CONFIGURATION ---
# Choose your AI provider
PROVIDER = "gemini"  # Options: "gemini" or "openai"
MODE = "professional" # Options: "professional" (OSINT Dossier) or "roast" (Mean/Funny)

# 🔑 API SETUP
if PROVIDER == "gemini":
    import google.generativeai as genai
    # ⚠️ REPLACE WITH YOUR ACTUAL API KEY
    genai.configure(api_key="AIzaSyAM71N2w06oqeTY4RNLLCgsIwgjMbA_xFc") 
    model = genai.GenerativeModel("gemini-2.0-flash-exp") # Flash is faster and has a larger context window

elif PROVIDER == "openai":
    from openai import OpenAI
    # ⚠️ REPLACE WITH YOUR ACTUAL API KEY
    client = OpenAI(api_key="YOUR_OPENAI_KEY")

RESPONSE_DIR = "./responses"

def extract_vision_data(json_data, filename):
    """
    Parses raw Google Vision API JSON to extract every scrap of forensic detail.
    """
    log = [f"\n--- 📁 ANALYSIS OF IMAGE: {filename} ---"]
    
    # Handle list vs dict response structure from Vision API
    try:
        if isinstance(json_data, dict) and "responses" in json_data:
            res = json_data["responses"][0]
        elif isinstance(json_data, list) and len(json_data) > 0:
            res = json_data[0]
        else:
            res = json_data 
            
        # 1. OCR TEXT & REGEX EXTRACTION (Dates, Captions, Names)
        if "textAnnotations" in res and res["textAnnotations"]:
            # First element is always the full text block
            full_text = res["textAnnotations"][0].get("description", "")
            
            # Pre-filter for handles (@username) to aid the AI
            handles = re.findall(r"(@\w+)", full_text)
            
            # Clean up newlines for the report readability
            clean_text = full_text.replace("\n", " | ")
            
            log.append(f"📜 OCR TEXT CONTENT: {clean_text}")
            if handles:
                log.append(f"🆔 DETECTED HANDLES: {', '.join(handles)}")
        else:
            log.append("📜 OCR TEXT CONTENT: [No text detected]")

        # 2. LABELS (Context clues like 'Wedding', 'Screenshot', 'Food')
        if "labelAnnotations" in res:
            labels = [label['description'] for label in res["labelAnnotations"][:12]]
            log.append(f"🏷️ CONTEXT LABELS: {', '.join(labels)}")

        # 3. OBJECTS (Physical items like 'Car', 'Person', 'Mobile Phone')
        if "localizedObjectAnnotations" in res:
            objects = [obj['name'] for obj in res["localizedObjectAnnotations"]]
            log.append(f"📦 PHYSICAL OBJECTS: {', '.join(objects)}")

        # 4. WEB ENTITIES (Internet context/Memes/Specific Landmarks)
        if "webDetection" in res and "webEntities" in res["webDetection"]:
            entities = [ent['description'] for ent in res["webDetection"]["webEntities"] if 'description' in ent][:8]
            log.append(f"🌐 WEB/INTERNET CONTEXT: {', '.join(entities)}")
            
        # 5. FACIAL EMOTIONS (Sentiment Analysis)
        if "faceAnnotations" in res:
            emotions = []
            for i, face in enumerate(res["faceAnnotations"]):
                if face.get("joyLikelihood") in ["LIKELY", "VERY_LIKELY"]: emotions.append(f"Face {i+1}: Joy")
                if face.get("angerLikelihood") in ["LIKELY", "VERY_LIKELY"]: emotions.append(f"Face {i+1}: Anger")
                if face.get("sorrowLikelihood") in ["LIKELY", "VERY_LIKELY"]: emotions.append(f"Face {i+1}: Sorrow")
            if emotions:
                log.append(f"😊 DETECTED EMOTIONS: {', '.join(emotions)}")

    except Exception as e:
        log.append(f"⚠️ Error parsing file data: {str(e)}")

    return "\n".join(log)

# --- MAIN LOADER ---

all_extracted_text = ""
file_count = 0

print(f"📂 Scanning directory: {RESPONSE_DIR}...")

if os.path.exists(RESPONSE_DIR):
    for filename in os.listdir(RESPONSE_DIR):
        if filename.lower().endswith(".json"):
            path = os.path.join(RESPONSE_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    # Process the raw vision data
                    extracted_info = extract_vision_data(data, filename)
                    all_extracted_text += extracted_info + "\n" + "="*50
                    file_count += 1
                except json.JSONDecodeError:
                    print(f"⚠️ Skipping invalid JSON file: {filename}")
else:
    print(f"❌ Directory '{RESPONSE_DIR}' not found.")
    exit()

print(f"✅ Successfully parsed {file_count} Vision API response files.")

# --- PROMPT ENGINEERING ---

if MODE == "professional":
    system_instruction = """
    You are an expert Open Source Intelligence (OSINT) analyst and Behavioral Profiler. 
    You have been provided with raw computer vision data (OCR text, object detection, labels) from a target's photo stream (likely Instagram).
    
    YOUR MISSION: Construct a comprehensive "Target Dossier" by cross-referencing all data points.

    ### 🕵️‍♂️ ANALYSIS DIRECTIVES:

    1. **IDENTITY & ASSOCIATES (High Priority):**
       - **Target ID:** Identify the main user handle/name appearing at the top of screenshots.
       - **Network Mapping:** Extract names of friends, commenters, and people tagged.
       - **Relationship Dynamics:** Analyze comment sentiment. (e.g., "Love you" = Partner/Close Friend, "Sir" = Professional, "HBD" = Birthday).
    
    2. **TEMPORAL RECONSTRUCTION (Timeline):**
       - **Absolute Dates:** Locate specific dates in text (e.g., "August 30").
       - **Relative Dates:** Convert timestamps like "7w ago" into estimated real-world months relative to the other dates found.
       - **Life Events:** Identify birthdays, anniversaries, or festivals based on captions + dates.

    3. **GEOSPATIAL & LIFESTYLE:**
       - **Location Inference:** Use shop names, landmarks (Web Entities), or language (e.g., Malayalam text implies Kerala, India) to pinpoint location.
       - **Status & Interests:** Infer hobbies from objects (gaming consoles, bikes, gym gear) and clothing styles.

    ### 📝 OUTPUT FORMAT (Structured Dossier):

    ## 👤 TARGET IDENTITY
    * **Handle/Name:** [Inferred Name]
    * **Est. Age/Gender:** [Based on photos/context]
    * **Location:** [Inferred City/Region]
    * **Key Life Event:** [e.g., "Birthday on August 30"]

    ## 🕸️ SOCIAL GRAPH
    | Name/Handle | Relationship | Evidence/Context |
    | :--- | :--- | :--- |
    | @username | [e.g. Best Friend] | [e.g. "Commented 'My bro' on 3 posts"] |

    ## 📅 CHRONOLOGICAL TIMELINE
    * **[Date/Timeframe]:** [Activity] (e.g., "Attended a wedding wearing traditional Mundu")
    * **[Date/Timeframe]:** [Activity]

    ## 🧠 PSYCHOLOGICAL PROFILE
    * **Personality:** [Introverted/Extroverted/Vanity metrics]
    * **Interests:** [List hobbies based on visual evidence]
    """

else: # ROAST MODE
    system_instruction = """
    You are a savage, observant social media roastmaster. 
    You are reading the raw forensic data of someone's photo gallery.
    
    Your Job:
    1. **Roast their Friends:** Call out specific names found in the OCR text.
    2. **Mock the Timeline:** If they posted "7w ago" and it's a boring photo, destroy them for it.
    3. **Expose the Vanity:** Look at the objects (Selfies? Gym mirrors?) and roast their ego.
    4. **The "Real" Profile:** Tell them who they *actually* are based on this data.
    
    Be mean, specific, and hilarious. Use the names you find.
    """

full_prompt = f"""{system_instruction}

--- RAW FORENSIC DATA STREAM ---

{all_extracted_text}

--- END OF DATA STREAM ---
"""

# --- SEND TO AI ---

profile_output = ""
print(f"\n🤖 Generating {MODE.upper()} report using {PROVIDER.upper()}...")

try:
    if PROVIDER == "gemini":
        response = model.generate_content(full_prompt)
        profile_output = response.text
    elif PROVIDER == "openai":
        chat_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a forensic data analyst."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7,
        )
        profile_output = chat_response.choices[0].message.content

except Exception as e:
    profile_output = f"❌ API Error: {str(e)}"

# --- OUTPUT TO CONSOLE & FILE ---

print("\n" + "#"*60)
print(profile_output)
print("#"*60 + "\n")

# Save to file
output_filename = f"social_dossier_{MODE}.txt"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(profile_output)

print(f"✅ Full Intelligence Report saved to: {os.path.abspath(output_filename)}")