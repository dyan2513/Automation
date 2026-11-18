"""Step 4: click the button that assigns the open ticket to you (skips if it is already assigned)."""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from settings import pause, STEP_DELAY, ACTION_DELAY

ASSIGN_BTN = (By.XPATH, '//*[@id="root"]/div/main/div/div/div[2]/div[1]/div[1]/div/div[1]/div[3]/button')

def assign_ticket(driver):
    # Short wait: if the ticket is already assigned, the button may not exist
    try:
        btn = WebDriverWait(driver, 6).until(EC.presence_of_element_located(ASSIGN_BTN))
    except Exception:
        print("No assign button found: the ticket is probably already assigned. Skipping.")
        return False

    label = (btn.text or "").strip()
    print("Button at the assign spot says:", label or "(no text)")

    # Only click if it really looks like an 'assign to me' button
    words = label.lower()
    looks_right = any(w in words for w in ("assign", "take", "claim")) and not any(
        w in words for w in ("unassign", "reassign", "release"))
    if not looks_right:
        print("That doesn't look like 'assign to me' (ticket is likely already assigned). Skipping.")
        return False

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(ACTION_DELAY)
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    time.sleep(ACTION_DELAY)
    print("Assigned the ticket to you.")
    return True

if __name__ == "__main__":
    from step1_open_site import open_site
    d = open_site()
    input("Log in, open a ticket by hand, then press Enter... ")
    assign_ticket(d)
    input("Press Enter to close...")
    d.quit()