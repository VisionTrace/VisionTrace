import os
import requests

# API endpoint
url = "https://api.theyseeyourphotos.com/deductions"

# Directory containing .png files
image_dir = "."

# Where to store responses
output_dir = "./responses"
os.makedirs(output_dir, exist_ok=True)

# Iterate through all .png files in directory
for filename in os.listdir(image_dir):
    if filename.lower().endswith(".png"):
        file_path = os.path.join(image_dir, filename)
        print(f"Uploading {file_path}...")

        with open(file_path, "rb") as f:
            files = {
                "file": (filename, f, "image/png"),
            }
            data = {
                "filename": filename,
                "language": "en"
            }
            
            try:
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()

                # Save response JSON/text for each file
                response_file = os.path.join(output_dir, f"{filename}.json")
                with open(response_file, "w", encoding="utf-8") as out:
                    out.write(response.text)

                print(f"✅ Response saved: {response_file}")
            except Exception as e:
                print(f"❌ Failed to upload {filename}: {e}")
