import uuid
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

profile_dir = tempfile.TemporaryDirectory(prefix="chrome_user_data_")
print(f"Temp profile: {profile_dir.name}")

options = Options()
options.binary_location = "/usr/bin/chromium"
options.add_argument(f"--user-data-dir={profile_dir.name}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
driver.get("https://www.google.com")
print("✅ Chrome started!")
driver.quit()