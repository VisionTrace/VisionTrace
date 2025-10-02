import os
import numpy as np
from collections import Counter
from PIL import Image, ImageOps
import face_recognition
from sklearn.cluster import DBSCAN
from tqdm import tqdm  # pip install tqdm scikit-learn pillow face_recognition

# --- CONFIGURATION ---
SOURCE_DIR = "instagram_posts"   # folder with your Instagram images
OWNER_DIR = "owner"              # where cropped owner faces will be saved
MODEL = "hog"                    # "hog" = fast CPU, "cnn" = accurate (needs GPU + dlib compiled with CUDA)
EPS = 0.5                        # DBSCAN eps (smaller = stricter clustering)
MIN_SAMPLES = 2                  # DBSCAN min samples per cluster


def find_and_save_owner_face():
    if not os.path.isdir(SOURCE_DIR):
        print(f"Error: The source directory '{SOURCE_DIR}' does not exist.")
        return

    if not os.path.exists(OWNER_DIR):
        os.makedirs(OWNER_DIR)
        print(f"Created directory: {OWNER_DIR}")

    all_face_encodings = []
    encoding_info = {}

    image_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print(f"Error: No image files found in '{SOURCE_DIR}'.")
        return

    print(f"\n--- Analyzing {len(image_files)} images in '{SOURCE_DIR}' ---\n")

    # Step 1: Extract face encodings
    for i, filename in enumerate(tqdm(image_files, desc="Processing images")):
        image_path = os.path.join(SOURCE_DIR, filename)

        try:
            image = Image.open(image_path)
            image = ImageOps.exif_transpose(image)  # Fix orientation
            np_image = np.array(image)

            face_locations = face_recognition.face_locations(np_image, model=MODEL)
            face_encodings = face_recognition.face_encodings(np_image, face_locations)

            for j, encoding in enumerate(face_encodings):
                all_face_encodings.append(encoding)
                encoding_info[len(all_face_encodings) - 1] = {
                    "path": image_path,
                    "filename": filename,
                    "location": face_locations[j]
                }
        except Exception as e:
            print(f"⚠️ Could not process {filename}. Reason: {e}")

    if not all_face_encodings:
        print("No faces detected in any images.")
        return

    print(f"\nFound {len(all_face_encodings)} total faces. Running clustering...")

    # Step 2: Cluster with DBSCAN
    encodings_array = np.array(all_face_encodings)
    clustering = DBSCAN(metric="euclidean", eps=EPS, min_samples=MIN_SAMPLES).fit(encodings_array)
    face_labels = clustering.labels_

    # Step 3: Identify the most frequent person (the "owner")
    label_counts = Counter(face_labels)
    if -1 in label_counts:  # -1 = noise (unclustered)
        del label_counts[-1]

    if not label_counts:
        print("Could not find a consistent owner face.")
        return

    most_frequent_id, frequency = label_counts.most_common(1)[0]
    print(f"✅ The most frequent person appears {frequency} times.")

    # Step 4: Save cropped faces
    saved_count = 0
    for i, label in enumerate(face_labels):
        if label == most_frequent_id:
            info = encoding_info[i]
            image_path = info["path"]
            filename = os.path.splitext(info["filename"])[0]
            top, right, bottom, left = info["location"]

            image = Image.open(image_path)
            image = ImageOps.exif_transpose(image)
            face_image = image.crop((left, top, right, bottom))

            output_path = os.path.join(OWNER_DIR, f"{filename}_owner_{saved_count}.png")
            face_image.save(output_path)
            saved_count += 1

    print(f"\n--- Done! ---")
    print(f"Saved {saved_count} cropped faces of the owner into '{OWNER_DIR}/' ✅")


if __name__ == "__main__":
    find_and_save_owner_face()
