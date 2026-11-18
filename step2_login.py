"""Step 2: log in. Asks for your email and password in the terminal
(or reads SIM_USER / SIM_PASS if set). Never type your password in the code."""
import os, time
from getpass import getpass
from settings import pause, STEP_DELAY, ACTION_DELAY
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# OPTIONAL: type your login here to skip the terminal prompts (local use only, never share this file)
EMAIL = ""
PASSWORD = ""

# Header button that brings up the login form (used only if the form isn't already visible)
OPEN_LOGIN_BTN = (By.XPATH, "//button[normalize-space()='Log In'] | //a[normalize-space()='Log In']")

# Exact XPaths you copied from Chrome
EMAIL_BOX  = (By.XPATH, '//*[@id="auth-section"]/div/div[2]/div/form/div[1]/input')
PASS_BOX   = (By.XPATH, '//*[@id="auth-section"]/div/div[2]/div/form/div[2]/div[1]/input')
SUBMIT_BTN = (By.XPATH, '//*[@id="auth-section"]/div/div[2]/div/form/button')

def _visible(driver, locator):
    return any(e.is_displayed() for e in driver.find_elements(*locator))

def fill(driver, el, text, label):
    """Type into a field; if the site ignores normal typing (React forms), set the value with JavaScript."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].focus();", el)
    el.click()
    el.clear()
    el.send_keys(text)
    if el.get_attribute("value") != text:
        driver.execute_script("""
            const el = arguments[0], val = arguments[1];
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, el, text)
    ok = el.get_attribute("value") == text
    print(f"Filled {label}: {'OK' if ok else 'FAILED'}")

def login(driver):
    wait = WebDriverWait(driver, 15)
    time.sleep(2)   # let the page finish loading

    # 0) Already logged in from a previous run? (Chrome remembers the session)
    if not _visible(driver, OPEN_LOGIN_BTN) and not _visible(driver, EMAIL_BOX):
        print("Already logged in (saved session). Skipping login.")
        return

    # 1) Bring up the login form if it isn't showing yet
    if not _visible(driver, EMAIL_BOX):
        btns = [b for b in driver.find_elements(*OPEN_LOGIN_BTN) if b.is_displayed()]
        if btns:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btns[0])
            driver.execute_script("arguments[0].click();", btns[0])
            print("Clicked Log In. Current page:", driver.current_url)

    # 2) Make sure the form is there, scroll to it, then ask for credentials
    email_el = wait.until(EC.presence_of_element_located(EMAIL_BOX))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", email_el)
    wait.until(EC.visibility_of_element_located(EMAIL_BOX))

    user = EMAIL or os.getenv("SIM_USER") or input("Email (type it HERE in the terminal, then press Enter): ")
    pw = PASSWORD or os.getenv("SIM_PASS") or getpass("Password (type it HERE, it stays hidden, then press Enter): ")

    # 3) Fill in and submit
    fill(driver, email_el, user, "email")
    time.sleep(ACTION_DELAY)
    pass_el = wait.until(EC.visibility_of_element_located(PASS_BOX))
    fill(driver, pass_el, pw, "password")
    time.sleep(ACTION_DELAY)
    start_url = driver.current_url
    btn = wait.until(EC.presence_of_element_located(SUBMIT_BTN))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    try:
        btn.click()
    except Exception:
        pass_el.send_keys(Keys.ENTER)       # fallback: press Enter in the password box
    print("Login submitted, waiting for the site to respond...")

    # 4) Check what happened (so we know WHY it failed, not just that it did)
    time.sleep(max(4, STEP_DELAY))
    print("URL before:", start_url)
    print("URL after: ", driver.current_url)
    form_still_there = _visible(driver, PASS_BOX)
    if form_still_there:
        print("The login form is STILL showing -> login did not go through.")
        driver.save_screenshot("login_result.png")
        print("Saved screenshot: login_result.png (check for an error message / CAPTCHA)")
        for e in driver.find_elements(By.CSS_SELECTOR, "[role='alert'], .error, [class*='error'], [class*='red']"):
            if e.is_displayed() and e.text.strip():
                print("Page message:", e.text.strip()[:200])
    else:
        print("Login form is gone -> login looks successful.")

if __name__ == "__main__":
    from step1_open_site import open_site
    d = open_site()
    login(d)
    input("Press Enter to close...")
    d.quit()