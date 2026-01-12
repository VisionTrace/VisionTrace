import base64
import requests
import os
import json

# --- CONFIGURATION ---
API_KEY = "AIzaSyAAJCYysCC8XxDuL6aQ5SMryyBKl8rlNDE"  # ⚠️ Replace with your actual API key
VISION_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

INPUT_FOLDER = "instagram_posts"
OUTPUT_FOLDER = "responses"

# --- FEATURES TO REQUEST ---
# We request a comprehensive list of features for maximum data
FEATURES_LIST = [
    {"type": "LABEL_DETECTION", "maxResults": 20},
    {"type": "TEXT_DETECTION"},
    {"type": "OBJECT_LOCALIZATION"},
    {"type": "FACE_DETECTION"},
    {"type": "LOGO_DETECTION"},
    {"type": "LANDMARK_DETECTION"},
    {"type": "SAFE_SEARCH_DETECTION"},
    {"type": "IMAGE_PROPERTIES"},
    {"type": "WEB_DETECTION"}  # Added Web Detection for context
]

def analyze_and_save(image_filename):
    """
    Reads an image, sends it to the Vision API, and saves the JSON response.
    """
    image_path = os.path.join(INPUT_FOLDER, image_filename)
    
    # 1. Encode image to Base64
    try:
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"❌ Error reading {image_filename}: {e}")
        return

    # 2. Construct the Request
    request_body = {
        "requests": [
            {
                "image": {"content": img_base64},
                "features": FEATURES_LIST
            }
        ]
    }

    # 3. Send Request to Google
    print(f"🚀 Sending {image_filename} to Vision API...")
    response = requests.post(VISION_URL, json=request_body)

    # 4. Handle Response
    if response.status_code == 200:
        result = response.json()
        
        # Construct the output filename (e.g., photo.jpg -> photo.json)
        base_name = os.path.splitext(image_filename)[0]
        json_filename = f"{base_name}.json"
        output_path = os.path.join(OUTPUT_FOLDER, json_filename)

        # 5. Save to File
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved analysis to: {output_path}")
    else:
        print(f"⚠️ API Error for {image_filename}: {response.status_code} - {response.text}")

def main():
    # 1. Check if input folder exists
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ Input folder '{INPUT_FOLDER}' not found. Please create it and add photos.")
        return

    # 2. Create output folder if it doesn't exist
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"📂 Created output folder: '{OUTPUT_FOLDER}'")

    # 3. Filter for valid image files
    valid_extensions = (".png", ".jpg", ".jpeg", ".webp")
    images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_extensions)]

    if not images:
        print(f"ℹ️ No images found in '{INPUT_FOLDER}'.")
        return

    print(f"🔍 Found {len(images)} images. Starting processing...\n")

    # 4. Process each image
    for image in images:
        analyze_and_save(image)

    print("\n🎉 All done! Check the 'responses' folder.")

if __name__ == "__main__":
    main()