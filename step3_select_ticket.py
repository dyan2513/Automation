"""Step 3: Scan the ticket queue, categorize each ticket (Onboarding, Offboarding,
Reset Password, User Authentication), and select a target ticket.
"""
from settings import pause, STEP_DELAY, ACTION_DELAY, TARGET_CATEGORY
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ticket_classifier import (
    classify_ticket, is_target_category,
    CATEGORY_ONBOARDING, CATEGORY_OFFBOARDING,
    CATEGORY_RESET_PASSWORD, CATEGORY_USER_AUTHENTICATION, CATEGORY_GENERAL
)

# Ticket card locators
TOP_TICKET = (By.XPATH, '//*[@id="root"]/div/main/div/div/div[2]/section/div[2]/div[1]/div/button')
ALL_TICKETS = (By.XPATH, '//*[@id="root"]/div/main/div/div/div[2]/section/div[2]/div/div/button')
TICKETS_URL = ""

def _use_open_window(driver):
    """If the window the script was using got closed, switch to one that is still open."""
    try:
        driver.current_url
    except Exception:
        if not driver.window_handles:
            raise SystemExit("The Chrome window was closed. Run the script again and leave Chrome open.")
        driver.switch_to.window(driver.window_handles[-1])

def select_ticket(driver, target_category=TARGET_CATEGORY):
    """Scans the ticket list, classifies tickets, and opens the best matching ticket.
    Returns: (body_text, ticket_title, ticket_category)
    """
    wait = WebDriverWait(driver, 15)

    # 1. If a ticket is already open, detect its category directly from page text
    if "#ticket/" in driver.current_url:
        print("\nA ticket is already open:", driver.current_url)
        body = driver.find_element(By.TAG_NAME, "main").text
        # Extract title from h1 or h2 or first line
        title = body.splitlines()[0] if body else "Current Ticket"
        category = classify_ticket(title=title, body=body)
        print(f"Detected Category: [{category}]")
        return body, title, category

    # 2. Navigate to tickets page if URL configured
    if TICKETS_URL:
        driver.get(TICKETS_URL)
        pause(ACTION_DELAY, "loading the ticket list")

    # 3. Wait for ticket cards to appear
    try:
        wait.until(EC.presence_of_element_located(ALL_TICKETS))
    except Exception:
        _use_open_window(driver)
        print("\nCouldn't find the ticket list on this page:", driver.current_url)
        input("In the Chrome window, open the ticket list yourself, then press Enter here... ")
        print("Now on:", driver.current_url, "  <- put this address in TICKETS_URL to skip this next time")
        wait.until(EC.presence_of_element_located(ALL_TICKETS))

    ticket_elements = driver.find_elements(*ALL_TICKETS)
    print(f"\nFound {len(ticket_elements)} ticket(s) in queue:")

    classified_tickets = []
    chosen_index = 0
    chosen_category = CATEGORY_GENERAL

    for i, btn in enumerate(ticket_elements):
        try:
            h3 = btn.find_element(By.TAG_NAME, "h3").text
        except Exception:
            h3 = btn.text.splitlines()[0] if btn.text else f"Ticket #{i+1}"

        desc_snippet = btn.text
        cat = classify_ticket(title=h3, body=desc_snippet)
        matches = is_target_category(cat, target_category)
        marker = " [TARGET MATCH]" if matches else ""
        print(f"  {i+1}. {h3} -> [{cat}]{marker}")

        classified_tickets.append((btn, h3, cat, matches))

    # Pick the first matching ticket, or top ticket as fallback
    matched = [item for item in classified_tickets if item[3]]
    if matched:
        chosen_btn, chosen_title, chosen_category, _ = matched[0]
        print(f"\n-> Selected target ticket: '{chosen_title}' [{chosen_category}]")
    elif classified_tickets:
        chosen_btn, chosen_title, chosen_category, _ = classified_tickets[0]
        print(f"\n-> No specific '{target_category}' match; opening top ticket: '{chosen_title}' [{chosen_category}]")
    else:
        chosen_btn = wait.until(EC.element_to_be_clickable(TOP_TICKET))
        chosen_title = "Top Ticket"
        chosen_category = CATEGORY_GENERAL

    # Open the selected ticket
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", chosen_btn)
    pause(ACTION_DELAY, "opening the ticket")
    chosen_btn.click()
    pause(ACTION_DELAY, "letting the ticket page load")

    body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "main"))).text
    # Re-evaluate category with full ticket body text
    final_category = classify_ticket(title=chosen_title, body=body)
    print(f"\nOpened ticket: {chosen_title}")
    print(f"Verified Category: [{final_category}]")
    return body, chosen_title, final_category

if __name__ == "__main__":
    from step1_open_site import open_site
    d = open_site()
    input("Make sure you're logged in and on the ticket list, then press Enter... ")
    select_ticket(d)
    input("Press Enter to close...")
    d.quit()
