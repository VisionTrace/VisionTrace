import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time

# Your Instagram credentials
USERNAME = "visiontrace26"
PASSWORD = "vision@2026"

# --- NEW ---
# Check command-line arguments
if len(sys.argv) < 2:
    print("Usage: python scrape.py <instagram_username>")
    sys.exit(1)

TARGET_USERNAME = sys.argv[1]

# --- NEW ---
# Define the directory to save photos and logs
OUTPUT_DIR = "instagram_posts"

# --- NEW ---
# Create the directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Chrome setup
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

def get_tagged_users():
    tagged_usernames = set()
    # Tagged overlays (on image)
    try:
        overlay_tags = driver.find_elements(By.XPATH, "//a[contains(@href, '/')]")
        for tag in overlay_tags:
            href = tag.get_attribute("href")
            txt = tag.text.strip()
            if txt.startswith('@') and len(txt) > 1:
                tagged_usernames.add(txt)
            elif '/users/' in href and txt:
                tagged_usernames.add(txt)
    except Exception as e:
        print(f"Overlay tags not found: {e}")
    # Caption mentions (@username in caption)
    try:
        caption_tags = driver.find_elements(By.XPATH, "//div[contains(@class,'C4VMK')]//a")
        for tag in caption_tags:
            txt = tag.text.strip()
            if txt.startswith('@') and len(txt) > 1:
                tagged_usernames.add(txt)
    except Exception as e:
        print(f"Caption tags not found: {e}")
    return list(tagged_usernames)

# Login to Instagram
driver.get("https://www.instagram.com/accounts/login/")
time.sleep(5)
driver.find_element(By.NAME, "username").send_keys(USERNAME)
driver.find_element(By.NAME, "password").send_keys(PASSWORD)
driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
time.sleep(7)  # Wait for login

# Go to target profile
profile_url = f"https://www.instagram.com/{TARGET_USERNAME}/"
driver.get(profile_url)
time.sleep(7)

# Scroll to load posts
for _ in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

# Collect post links
posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
post_links = [p.get_attribute("href") for p in posts]
print(f"Found {len(post_links)} posts.")

# Screenshot each post and show tagged users
for idx, link in enumerate(post_links):
    try:
        driver.get(link)
        time.sleep(5)
        screenshot_path = os.path.join(OUTPUT_DIR, f"post_{idx}.png")
        driver.save_screenshot(screenshot_path)
        
        tagged = get_tagged_users()
        print(f"Saved screenshot for {link} to {screenshot_path}")
        if tagged:
            print(f"Tagged users in post {idx}: {tagged}")
        else:
            print(f"No tagged users found in post {idx}")
    except Exception as e:
        print(f"Error with post {idx}: {e}")

# Tagged posts
tagged_url = profile_url + "tagged/"
driver.get(tagged_url)
time.sleep(7)
for _ in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

tagged_posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
tagged_links = [p.get_attribute("href") for p in tagged_posts]
print(f"Found {len(tagged_links)} tagged posts.")

for idx, link in enumerate(tagged_links):
    try:
        driver.get(link)
        time.sleep(5)
        screenshot_path = os.path.join(OUTPUT_DIR, f"tagged_post_{idx}.png")
        driver.save_screenshot(screenshot_path)

        tagged = get_tagged_users()
        print(f"Saved tagged screenshot for {link} to {screenshot_path}")
        if tagged:
            print(f"Tagged users in tagged post {idx}: {tagged}")
        else:
            print(f"No tagged users found in tagged post {idx}")
    except Exception as e:
        print(f"Error with tagged post {idx}: {e}")

# Save console logs
logs = driver.get_log('browser')
log_path = os.path.join(OUTPUT_DIR, "console_logs.txt")
with open(log_path, "w", encoding="utf-8") as f:
    for log in logs:
        f.write(f"{log['level']} - {log['message']}\n")

driver.quit()
