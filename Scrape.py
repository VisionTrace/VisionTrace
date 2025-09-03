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

# Chrome setup
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

# Login to Instagram
driver.get("https://www.instagram.com/accounts/login/")
time.sleep(5)

driver.find_element(By.NAME, "username").send_keys(USERNAME)
driver.find_element(By.NAME, "password").send_keys(PASSWORD)
driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
time.sleep(7)  # Wait for login

# Go to target profile
url = "https://www.instagram.com/_aravind_135/"
driver.get(url)
time.sleep(7)

# Scroll to load posts
for _ in range(5):  # scroll multiple times to load more posts
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

# Get all post links
posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
post_links = [p.get_attribute("href") for p in posts]
print(f"Found {len(post_links)} posts.")

# Visit each post and screenshot
for idx, link in enumerate(post_links):
    try:
        driver.get(link)
        time.sleep(5)  # wait for post to load
        driver.save_screenshot(f"post_{idx}.png")
        print(f"Saved screenshot for {link}")
    except Exception as e:
        print(f"Error with post {idx}: {e}")

# Save console logs
logs = driver.get_log('browser')
with open("console_logs.txt", "w", encoding="utf-8") as f:
    for log in logs:
        f.write(f"{log['level']} - {log['message']}\n")

driver.quit()
