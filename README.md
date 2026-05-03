# VisionTrace

**VisionTrace** is an advanced AI-powered OSINT (Open Source Intelligence) and profiling framework designed to automate digital footprint tracing and entity analysis.

---

## 📂 Directory Structure

To ensure the application functions correctly, create the following directory structure for storing media, responses, and results:

E:\Vision_Trace\Vision_Trace\data
├───images
│   └───instagram
├───responses
├───results
└───tweets

🛠️ Installation & Environment Setup
It is highly recommended to use a virtual environment (venv) to manage dependencies.

1. Initialize Virtual Environment
PowerShell
# Create the venv
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
2. Install Dependencies
Bash
pip install -r requirements.txt
🔐 Instagram Authentication
To bypass automated bot detection, you must provide valid session cookies.

Export Cookies: Use a browser extension (e.g., "EditThisCookie") while logged into Instagram.

Format: Export the cookies in JSON format.

File Placement: Save the file as insta_cookies.json inside the project root.

Security: Keep this file private; it contains your active login session.

🚀 Running the Application
VisionTrace can be run locally for development or via Gunicorn for production-grade stability.

Development Mode
Bash
python app.py
Production Mode (Gunicorn)
Use the following command to run the application as a production-ready web app:

Bash
gunicorn --workers 4 --bind 0.0.0.0:8000 app:app
--workers 4: Optimizes performance based on CPU cores.

--bind 0.0.0.0:8000: Makes the app accessible over your local network.

app:app: Refers to the app.py entry point and the application instance.

⚖️ Disclaimer
This tool is for educational and professional research purposes only. Always comply with the Terms of Service of the platforms being analyzed and local privacy laws.
