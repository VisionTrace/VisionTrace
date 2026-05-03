import json
import time
import sys
import random
import math
import requests
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from app.paths import (
    INSTAGRAM_COOKIE_FILE,
    insta_profile_dir,
    insta_posts_dir,
    insta_tagged_dir
)

# =========================================================
# CONFIGURATION
# =========================================================

# UPDATED: If total items > 30, use parallel processing (Turbo).
# If < 30, use sequential (Fast for small batches).
MULTIPROCESS_THRESHOLD = 30
MAX_WORKERS = 3

# =========================================================
# DRIVER FACTORY
# =========================================================

def create_driver(headless=True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # 1920x1080 is crucial for the sidebar (comments) to appear
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--mute-audio") # Silence reels
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

# =========================================================
# HELPERS
# =========================================================

def download_image(url: str, path):
    """Downloads profile picture."""
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
    except Exception:
        pass

def capture_element(driver, save_path):
    """
    Smart Capture: Tries to screenshot the <article> (post+sidebar).
    Falls back to full page if that fails.
    """
    try:
        # Wait specifically for the post container
        article = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", article)
        time.sleep(0.5) # Allow render
        article.screenshot(str(save_path))
        return True
    except:
        # Fallback
        try:
            driver.save_screenshot(str(save_path))
            return True
        except:
            return False

def scrape_links_from_tab(driver, max_scroll_fails=3):
    """Scrolls the current page to collect all unique post/reel links."""
    links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    unchanged_count = 0
    
    while True:
        # Collect visible links (Posts + Reels)
        els = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
        for el in els:
            links.add(el.get_attribute("href"))
            
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Check if we hit bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            unchanged_count += 1
            if unchanged_count >= max_scroll_fails:
                break
        else:
            unchanged_count = 0
        last_height = new_height
        
        # Safety limit (optional)
        if len(links) > 2000: break

    return list(links)

# =========================================================
# WORKER PROCESS (For Multiprocessing)
# =========================================================

def process_batch_worker(task_data):
    """Worker function that runs in a separate process."""
    links = task_data['links']
    username = task_data['username']
    category = task_data['category']
    worker_id = task_data['id']
    
    # Set correct directory
    if category == 'tagged':
        SAVE_DIR = insta_tagged_dir(username)
        prefix = "tagged"
    else:
        SAVE_DIR = insta_posts_dir(username)
        prefix = "post"

    print(f"[Worker {worker_id}] Processing {len(links)} {category}...")
    
    driver = create_driver(headless=True)
    
    try:
        # Login is required for each worker
        driver.get("https://www.instagram.com/")
        time.sleep(2)
        if INSTAGRAM_COOKIE_FILE.exists():
            with open(INSTAGRAM_COOKIE_FILE, "r") as f:
                cookies = json.load(f)
            for c in cookies:
                c.pop("sameSite", None)
                try: driver.add_cookie(c)
                except: pass
            driver.refresh()
            time.sleep(3)

        count = 0
        for idx, link in enumerate(links):
            try:
                driver.get(link)
                time.sleep(random.uniform(1.5, 3.0))
                
                filename = f"{prefix}_w{worker_id}_{idx}.png"
                capture_element(driver, SAVE_DIR / filename)
                count += 1
            except:
                continue
        return count
    finally:
        driver.quit()

# =========================================================
# MAIN SCRAPER FUNCTION
# =========================================================

def run_scrape(username: str) -> Dict[str, Any]:

    if not INSTAGRAM_COOKIE_FILE.exists():
        raise RuntimeError("Instagram cookie file missing")

    # Ensure directories exist
    PROFILE_DIR = insta_profile_dir(username)
    POSTS_DIR = insta_posts_dir(username)
    TAGGED_DIR = insta_tagged_dir(username)

    # --- PHASE 1: PROFILE INFO & LINK COLLECTION ---
    print(f"--- Accessing Profile: {username} ---")
    driver = create_driver(headless=True)
    wait = WebDriverWait(driver, 20)
    
    post_links = []
    tagged_links = []
    about = {"username": username}
    
    try:
        # 1. Login
        driver.get("https://www.instagram.com/")
        time.sleep(2)
        with open(INSTAGRAM_COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        for c in cookies:
            c.pop("sameSite", None)
            try: driver.add_cookie(c)
            except: pass
        driver.refresh()
        time.sleep(4)

        # 2. Go to Profile
        url = f"https://www.instagram.com/{username}/"
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        time.sleep(3)
        
        # 3. Scrape Profile Details (Name, Bio, Stats)
        try:
            about["name"] = driver.find_element(By.XPATH, "//header//h2").text
        except: about["name"] = ""

        try:
            about["bio"] = driver.find_element(By.XPATH, "//header//section//div/span").text
        except: about["bio"] = ""

        try:
            stats = driver.find_elements(By.XPATH, "//header//li")
            if len(stats) >= 3:
                about["posts"] = stats[0].text
                about["followers"] = stats[1].text
                about["following"] = stats[2].text
        except: pass
        
        # Save JSON
        with open(PROFILE_DIR / "profile_about.json", "w", encoding="utf-8") as f:
            json.dump(about, f, indent=2, ensure_ascii=False)
            
        # 4. Download Profile Picture
        try:
            img = driver.find_element(By.XPATH, "//header//img")
            pic_url = img.get_attribute("src")
            download_image(pic_url, PROFILE_DIR / "profile_pic.jpg")
        except: pass

        # Screenshot Profile Header
        driver.save_screenshot(str(PROFILE_DIR / "profile_about.png"))
        print("Profile details saved.")

        # 5. Collect Post Links (Infinite Scroll)
        print("Collecting post links...")
        post_links = scrape_links_from_tab(driver)
        print(f"Found {len(post_links)} total posts/reels.")
        
        # 6. Collect Tagged Links
        print("Collecting tagged links...")
        driver.get(url + "tagged/")
        time.sleep(3)
        tagged_links = scrape_links_from_tab(driver)
        print(f"Found {len(tagged_links)} tagged posts.")
        
        total_items = len(post_links) + len(tagged_links)

        # --- PHASE 2: PROCESSING (HYBRID MODE) ---
        
        # Mode A: Sequential (Reuse current browser for small batches)
        if total_items < MULTIPROCESS_THRESHOLD:
            print(f"--- Fast Sequential Mode (< {MULTIPROCESS_THRESHOLD} items) ---")
            
            p_count = 0
            for i, link in enumerate(post_links):
                driver.get(link)
                time.sleep(1.5)
                capture_element(driver, POSTS_DIR / f"post_{i}.png")
                p_count += 1
                
            t_count = 0
            for i, link in enumerate(tagged_links):
                driver.get(link)
                time.sleep(1.5)
                capture_element(driver, TAGGED_DIR / f"tagged_{i}.png")
                t_count += 1
            
            driver.quit()
            return {
                "status": "success", "mode": "sequential",
                "profile": about,
                "posts_scraped": p_count, "tagged_scraped": t_count
            }

        # Mode B: Multiprocessing (Spin up workers for large batches)
        else:
            print(f"--- Turbo Multiprocessing Mode ({total_items} items) ---")
            driver.quit() # Close collector to free resources
            
            tasks = []
            
            # Chunk Posts
            if post_links:
                chunk_s = math.ceil(len(post_links) / MAX_WORKERS)
                for i in range(0, len(post_links), chunk_s):
                    tasks.append({
                        'id': len(tasks)+1, 'username': username, 
                        'category': 'posts', 'links': post_links[i:i+chunk_s]
                    })
            
            # Add Tagged
            if tagged_links:
                tasks.append({
                    'id': len(tasks)+1, 'username': username, 
                    'category': 'tagged', 'links': tagged_links
                })

            total_scraped = 0
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                results = executor.map(process_batch_worker, tasks)
                for res in results:
                    total_scraped += res
                    
            return {
                "status": "success", "mode": "multiprocessing",
                "profile": about,
                "total_captured": total_scraped
            }

    except Exception as e:
        if driver: driver.quit()
        return {"status": "error", "message": str(e)}

# =========================================================
# EXECUTION
# =========================================================

if __name__ == "__main__":
    # Required for Windows Multiprocessing
    multiprocessing.freeze_support()
    
    if len(sys.argv) != 2:
        print("Usage: python -m modules.instagram.scrape <username>")
        exit(1)

    start_time = time.time()
    result = run_scrape(sys.argv[1])
    print(f"\nCompleted in {time.time() - start_time:.2f} seconds.")
    print(result)
