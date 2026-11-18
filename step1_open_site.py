"""Step 1: open Chrome and go to Service Desk Simulator."""
import os
from selenium import webdriver

URL = "https://servicedesk-simulator.com"

# Chrome remembers your login in this folder (created next to the script), so you only log in once
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

def open_site():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.get(URL)
    print("Opened:", driver.title)
    return driver

if __name__ == "__main__":      # run this file alone to test just this step
    d = open_site()
    input("Press Enter to close...")
    d.quit()