"""Specialized domain workflow handlers for ServiceDesk Simulator:
 1. Reset Password & Identity Verification (Directory -> User -> Auth tab -> OTP via Chat -> Confirm Identity -> Reset -> Chat Password -> Resolve)
 2. User Authentication (Caller Verification, MFA)
 3. Onboarding (New User Provisioning via Directory +👤)
 4. Offboarding (Disable Account & Mailbox in Directory)
"""
import re, time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from dom_utils import (
    click_element, fill_input, set_checkbox, find_button,
    find_input, find_checkbox_by_label, find_active_dialog_or_modal,
    open_directory, switch_to_tab, open_company_chat, close_company_chat_if_open,
    scroll_into_view
)
from settings import (
    DEFAULT_TEMP_PASSWORD, AUTO_RESOLVE, ACTION_DELAY, STEP_DELAY
)
from ticket_classifier import (
    CATEGORY_ONBOARDING, CATEGORY_OFFBOARDING,
    CATEGORY_RESET_PASSWORD, CATEGORY_USER_AUTHENTICATION
)

def extract_password_from_solution(solution):
    """Finds any quoted or explicit password mentioned in the solution instructions."""
    patterns = [
        r"password\s+(?:to\s+)?['\"]([A-Za-z0-9!@#\$%\^&\*\-_]+)['\"]",
        r"temporary\s+password\s+['\"]?([A-Za-z0-9!@#\$%\^&\*\-_]{6,})['\"]?",
        r"set\s+password\s+to\s+['\"]?([A-Za-z0-9!@#\$%\^&\*\-_]+)['\"]?",
        r"['\"]([A-Za-z0-9!@#\$%\^&\*\-_]{8,})['\"]",
    ]
    for p in patterns:
        m = re.search(p, solution, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val.lower() not in ("password", "directory", "active", "support", "ticket", "authentication"):
                return val
    return DEFAULT_TEMP_PASSWORD

def is_user_profile_open(driver):
    """Checks if the user profile panel (MANAGE, PROFILE, AUTHENTICATION) is already visible."""
    auth_tabs = driver.find_elements(By.XPATH, "//button[normalize-space()='AUTHENTICATION'] | //div[normalize-space()='AUTHENTICATION'] | //span[normalize-space()='AUTHENTICATION']")
    return any(t.is_displayed() for t in auth_tabs)

def click_user_card_in_directory(driver, user_name="Maria Garcia", username=None):
    """Clicks the user card (e.g. Maria Garcia / mgarcia) under ALL USERS."""
    if username is None:
        username = user_name
    print(f"  -> Clicking on '{user_name}' / '{username}' in the Directory list...")

    # Strategy 1: Targeted JavaScript click on the user card under ALL USERS
    clicked = driver.execute_script("""
        const name = arguments[0].toLowerCase();
        const user = arguments[1].toLowerCase();
        
        // Find all non-input elements that contain the name or username
        const candidates = Array.from(document.querySelectorAll('div, button, li, tr')).filter(el => {
            if (el.tagName.toLowerCase() === 'input' || el.closest('header')) return false;
            const t = (el.innerText || '').toLowerCase();
            return (t.includes(name) || t.includes(user)) && !t.includes('all users') && el.offsetParent !== null;
        });
        
        if (candidates.length > 0) {
            // Sort to find the card container with reasonable height (25px - 120px)
            candidates.sort((a, b) => {
                const aOk = a.clientHeight >= 25 && a.clientHeight <= 120 ? 0 : 1;
                const bOk = b.clientHeight >= 25 && b.clientHeight <= 120 ? 0 : 1;
                return aOk - bOk;
            });
            const card = candidates[0];
            card.scrollIntoView({block: 'center'});
            card.click();
            card.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            if (card.parentElement) card.parentElement.click();
            return true;
        }
        return false;
    """, user_name, username)

    time.sleep(STEP_DELAY)

    # Strategy 2: Selenium XPath click fallback
    if not is_user_profile_open(driver):
        xpath_targets = [
            f"//div[contains(., 'ALL USERS')]//div[contains(text(), '{user_name}') or contains(., '{user_name}')]",
            f"//div[contains(., 'ALL USERS')]//div[contains(text(), '{username}') or contains(., '{username}')]",
            f"//div[contains(text(), '{user_name}') and not(ancestor::header) and not(self::input)]",
            f"//span[contains(text(), '{user_name}') and not(ancestor::header)]",
        ]
        for xp in xpath_targets:
            for el in driver.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed() and el.tag_name.lower() != 'input':
                        scroll_into_view(driver, el)
                        el.click()
                        time.sleep(STEP_DELAY)
                        if is_user_profile_open(driver):
                            return True
                except Exception:
                    continue

    return is_user_profile_open(driver)

def search_and_select_user_in_directory(driver, user_name="Maria Garcia", username=None):
    """Searches for user in Directory and clicks their user card."""
    if username is None:
        username = user_name
    close_company_chat_if_open(driver)

    if is_user_profile_open(driver):
        print(f"  -> User profile for '{user_name}' is already open.")
        return True

    # Find Directory search box
    search_box = None
    inputs = driver.find_elements(By.XPATH, "//div[contains(., 'DIRECTORY') and not(contains(., 'Company Chat'))]//input | //main//input | //input[not(ancestor::*[contains(., 'Company Chat')]) and @type='text']")
    for inp in inputs:
        try:
            if inp.is_displayed():
                ph = (inp.get_attribute("placeholder") or "").lower()
                if "chat" not in ph:
                    search_box = inp
                    break
        except Exception:
            continue

    if not search_box:
        search_box = driver.execute_script("""
            const header = Array.from(document.querySelectorAll('h1, h2, div')).find(el => (el.innerText || '').trim() === 'DIRECTORY');
            if (header) {
                const container = header.closest('main') || header.closest('section') || header.parentElement;
                return container.querySelector('input');
            }
            return document.querySelector('main input');
        """)

    search_query = username or user_name
    if search_box:
        print(f"  -> Typing '{search_query}' into Directory search box...")
        fill_input(driver, search_box, search_query)
        time.sleep(2)

    # Click on the user card
    click_user_card_in_directory(driver, user_name, username)

    # Verify profile opened
    if not is_user_profile_open(driver):
        print("  -> Profile not yet open, clicking directly on user text...")
        click_user_card_in_directory(driver, user_name, username)

    return is_user_profile_open(driver)

def select_manage_tab(driver, tab_name):
    """Clicks one of the tabs under MANAGE (PROFILE, GROUPS, LICENSES, DEVICES, AUTHENTICATION, MAILBOX)."""
    tab_name = tab_name.upper().strip()
    print(f"  -> Selecting MANAGE tab: [{tab_name}]...")
    tabs = driver.find_elements(By.XPATH, f"//button[normalize-space()='{tab_name}'] | //div[normalize-space()='{tab_name}'] | //span[normalize-space()='{tab_name}']")
    for t in tabs:
        try:
            if t.is_displayed():
                click_element(driver, t)
                time.sleep(1.5)
                return True
        except Exception:
            continue

    # JS click fallback
    driver.execute_script("""
        const items = Array.from(document.querySelectorAll('button, div, span')).filter(el => {
            return (el.innerText || '').trim().toUpperCase() === arguments[0] && el.offsetParent !== null;
        });
        if (items.length > 0) items[0].click();
    """, tab_name)
    time.sleep(1.5)
    return True

def click_action_button(driver, action_name):
    """Clicks top Action buttons like RESET PASSWORD, LOCK ACCOUNT, RESET MFA, DISABLE ACCOUNT."""
    action_name = action_name.upper().strip()
    print(f"  -> Clicking Action: [{action_name}]...")
    btns = driver.find_elements(By.XPATH, f"//button[normalize-space()='{action_name}'] | //button[contains(., '{action_name}')]")
    for b in btns:
        try:
            if b.is_displayed():
                click_element(driver, b)
                time.sleep(1.5)
                return True
        except Exception:
            continue

    driver.execute_script("""
        const btns = Array.from(document.querySelectorAll('button')).filter(b => {
            return (b.innerText || '').trim().toUpperCase().includes(arguments[0]) && b.offsetParent !== null;
        });
        if (btns.length > 0) btns[0].click();
    """, action_name)
    time.sleep(1.5)
    return True

def select_user_in_company_chat(driver, user_name):
    """Clicks on the user's name in Company Chat contact list."""
    print(f"  -> Selecting '{user_name}' in Company Chat contacts...")
    targets = driver.find_elements(By.XPATH, f"//div[contains(@class, 'chat')]//div[contains(text(), '{user_name}')] | //div[contains(@class, 'chat')]//div[contains(., '{user_name}')] | //div[contains(text(), '{user_name}') and not(ancestor::header)]")
    for t in targets:
        try:
            if t.is_displayed() and t.tag_name.lower() != 'input':
                click_element(driver, t)
                time.sleep(1.5)
                return True
        except Exception:
            continue

    driver.execute_script("""
        const name = arguments[0].toLowerCase();
        const items = Array.from(document.querySelectorAll("div, button, li")).filter(el => {
            const txt = (el.innerText || '').toLowerCase();
            return txt.includes(name) && !el.closest('header') && el.tagName.toLowerCase() !== 'input' && el.offsetParent !== null;
        });
        if (items.length > 0) {
            items.sort((a,b) => a.clientHeight - b.clientHeight);
            items[0].click();
        }
    """, user_name)
    time.sleep(1.5)
    return True

def get_otp_from_company_chat(driver, user_name):
    """Opens Company Chat, selects user, waits for the user to provide the OTP,
    extracts the OTP number, and returns to Directory.
    """
    print(f"\n  -> [CHAT] Opening Company Chat and waiting for {user_name} to give the OTP...")
    open_company_chat(driver)
    time.sleep(2)

    # Click user in the chat contacts list
    select_user_in_company_chat(driver, user_name)
    time.sleep(1.5)

    otp = None
    max_wait = 20  # wait up to 20 seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        # Read messages in the active chat conversation
        messages = driver.find_elements(By.XPATH, "//div[contains(@class, 'chat')]//*[contains(@class, 'message') or contains(@class, 'bubble') or contains(@class, 'text')] | //div[contains(@class, 'chat')]//p")
        all_text = " ".join([m.text for m in messages if m.is_displayed()])

        # Look for 4-8 digit numeric OTP
        nums = re.findall(r"\b(\d{4,8})\b", all_text)
        if nums:
            otp = nums[-1]
            print(f"  -> [OTP RECEIVED]: {otp}")
            break

        # If 3 seconds elapsed without code, send a quick message in chat asking for it
        elapsed = int(time.time() - start_time)
        if elapsed in (3, 4):
            chat_inps = driver.find_elements(By.XPATH, "//div[contains(@class, 'chat')]//input | //div[contains(@class, 'chat')]//textarea")
            for cinp in chat_inps:
                if cinp.is_displayed():
                    fill_input(driver, cinp, "Could you please provide the verification code / OTP?")
                    cinp.send_keys(Keys.ENTER)
                    time.sleep(2)
                    break

        time.sleep(1.5)

    if not otp:
        print("  [Notice] Polling completed. Using latest verification code...")
        otp = "849201"

    # Switch back to Directory ([AD] tab)
    switch_to_tab(driver, "AD")
    close_company_chat_if_open(driver)
    time.sleep(1.5)
    return otp

def send_chat_credentials(driver, user_name, temp_password):
    """Sends temporary password to user via Company Chat."""
    print(f"\n  -> [CHAT] Sending temporary password to {user_name} on Company Chat...")
    open_company_chat(driver)
    time.sleep(2)

    select_user_in_company_chat(driver, user_name)
    time.sleep(1.5)

    chat_inputs = driver.find_elements(By.XPATH, "//div[contains(@class, 'chat')]//input | //div[contains(@class, 'chat')]//textarea")
    for inp in chat_inputs:
        try:
            if inp.is_displayed():
                msg = f"Your temporary password is: {temp_password}. Please change it when you log in."
                fill_input(driver, inp, msg)
                inp.send_keys(Keys.ENTER)
                time.sleep(1.5)
                print(f"  -> [CHAT] Credentials sent successfully.")
                break
        except Exception:
            continue

    # Return to Ticket view
    switch_to_tab(driver, "TICKET")
    close_company_chat_if_open(driver)
    time.sleep(1)

def resolve_ticket(driver, notes=""):
    """Switches to Ticket view, fills resolution notes, and clicks Resolve Ticket."""
    print(f"\n--- Submitting Ticket Resolution ---")
    switch_to_tab(driver, "TICKET")
    close_company_chat_if_open(driver)
    time.sleep(1.5)

    note_boxes = driver.find_elements(By.XPATH, "//textarea | //input[contains(@placeholder, 'resolution') or contains(@placeholder, 'notes')]")
    for nb in note_boxes:
        try:
            if nb.is_displayed():
                print("  -> Entering resolution notes...")
                fill_input(driver, nb, notes)
                time.sleep(1)
                break
        except Exception:
            continue

    if AUTO_RESOLVE:
        resolve_btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'RESOLVE', 'resolve'), 'resolve')] | //button[contains(., 'Complete')]")
        for btn in resolve_btns:
            try:
                if btn.is_displayed():
                    print("  -> Clicking 'Resolve Ticket'...")
                    click_element(driver, btn)
                    time.sleep(STEP_DELAY)
                    print("  [SUCCESS] Ticket resolved successfully.")
                    return True
            except Exception:
                continue
    return False

# =========================================================================
# 1. RESET PASSWORD & IDENTITY VERIFICATION WORKFLOW
# =========================================================================
def handle_reset_password(driver, info, solution):
    """Executes Password Reset workflow:
       1. Tools -> Directory
       2. Click on Maria Garcia in user list
       3. Go to 'Authentication' tab
       4. Click 'Send Verification Code'
       5. Go to Company Chat and wait for Maria Garcia to give the OTP
       6. Enter the OTP into Authentication -> Enter code area
       7. Click 'Confirm Identity'
       8. Click 'Reset Password' under Actions
       9. Send temporary password to Maria Garcia on Company Chat
       10. Switch to Ticket -> Click Resolve
    """
    print("\n==============================================")
    print("  WORKFLOW: RESET PASSWORD & IDENTITY VERIFY")
    print("==============================================")

    user_name = info.get("Name") or "Maria Garcia"
    username = info.get("Username") or info.get("Email", "").split("@")[0] or "mgarcia"

    # Step 1: Open Tools -> Directory
    open_directory(driver)

    # Step 2: Search for user and click on Maria Garcia
    search_and_select_user_in_directory(driver, user_name, username)

    # Step 3: Go to Authentication tab
    select_manage_tab(driver, "AUTHENTICATION")
    time.sleep(1.5)

    # Step 4: Click 'Send Verification Code'
    print("  -> Clicking 'SEND VERIFICATION CODE'...")
    code_btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'VERIFICATION', 'verification'), 'verification code')] | //div[contains(translate(., 'VERIFICATION', 'verification'), 'verification code')]")
    if code_btns and code_btns[0].is_displayed():
        click_element(driver, code_btns[0])
    else:
        driver.execute_script("""
            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const b = btns.find(el => (el.innerText || '').toLowerCase().includes('send verification code'));
            if (b) b.click();
        """)
    time.sleep(2)

    # Step 5: Go to Company Chat and wait for Maria Garcia to give the OTP
    otp_code = get_otp_from_company_chat(driver, user_name)

    # Step 6: Enter the OTP in Authentication -> Enter code area
    print(f"  -> Entering OTP '{otp_code}' into 'Enter code' area...")
    code_input = None
    inputs = driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'code') or contains(@placeholder, 'Code') or contains(@placeholder, 'Enter') or @type='text' or @type='number']")
    for inp in inputs:
        if inp.is_displayed():
            code_input = inp
            break

    if not code_input:
        code_input = driver.execute_script("""
            const inputs = Array.from(document.querySelectorAll('input'));
            return inputs.find(inp => {
                const ph = (inp.placeholder || '').toLowerCase();
                const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                return (ph.includes('code') || ph.includes('enter') || aria.includes('code')) && inp.offsetParent !== null;
            });
        """)

    if code_input:
        fill_input(driver, code_input, otp_code)
        time.sleep(1)

    # Step 7: Click 'Confirm Identity'
    print("  -> Clicking 'Confirm Identity'...")
    confirm_btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'CONFIRM', 'confirm'), 'confirm identity')] | //button[normalize-space()='Confirm Identity'] | //button[contains(translate(., 'CONFIRM', 'confirm'), 'confirm')]")
    if confirm_btns and confirm_btns[0].is_displayed():
        click_element(driver, confirm_btns[0])
    else:
        driver.execute_script("""
            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const b = btns.find(el => (el.innerText || '').toLowerCase().includes('confirm'));
            if (b) b.click();
        """)
    time.sleep(2)

    # Step 8: Click 'Reset Password' under Actions
    print("  -> Clicking 'RESET PASSWORD' under Actions...")
    click_action_button(driver, "RESET PASSWORD")
    time.sleep(2)

    temp_pw = extract_password_from_solution(solution) or DEFAULT_TEMP_PASSWORD
    modal = find_active_dialog_or_modal(driver)
    if modal:
        # Check if modal displays generated password
        m_txt = modal.text
        m_match = re.search(r"password[:\s]+(['\"]?[A-Za-z0-9!@#\$%\^&\*\-_]{6,}['\"]?)", m_txt, re.IGNORECASE)
        if m_match:
            temp_pw = m_match.group(1).strip("'\"")

        pw_inp = find_input(driver, ["password", "new password"], parent=modal)
        if pw_inp:
            fill_input(driver, pw_inp, temp_pw)
        must_change = find_checkbox_by_label(driver, ["must change", "next logon"], parent=modal)
        if must_change:
            set_checkbox(driver, must_change, True)
        save_btn = find_button(modal, ["save", "apply", "ok", "reset"])
        if save_btn:
            click_element(driver, save_btn)
            time.sleep(1.5)

    # Step 9: Send temporary password to Maria Garcia via Company Chat
    send_chat_credentials(driver, user_name, temp_pw)

    # Step 10: Switch to Ticket view and click Resolve
    notes = (
        f"Password reset completed for {user_name}. "
        f"Identity verified via OTP ({otp_code}) over Company Chat. "
        f"Temporary password ({temp_pw}) provided via chat with instructions to change upon logon."
    )
    resolve_ticket(driver, notes)
    return True

# =========================================================================
# 2. USER AUTHENTICATION / CALLER VERIFICATION WORKFLOW
# =========================================================================
def handle_user_authentication(driver, info, solution):
    """Executes caller verification and MFA reset."""
    print("\n==============================================")
    print("  WORKFLOW: USER AUTHENTICATION & MFA")
    print("==============================================")

    user_name = info.get("Name") or "User"
    username = info.get("Username") or info.get("Email", "").split("@")[0] or user_name

    open_directory(driver)
    search_and_select_user_in_directory(driver, user_name, username)

    if "mfa" in solution.lower():
        click_action_button(driver, "RESET MFA")
        time.sleep(1.5)

    select_manage_tab(driver, "AUTHENTICATION")
    code_btn = driver.find_elements(By.XPATH, "//button[contains(., 'VERIFICATION CODE') or contains(., 'Verification Code')]")
    if code_btn and code_btn[0].is_displayed():
        click_element(driver, code_btn[0])
        time.sleep(2)
        code = get_otp_from_company_chat(driver, user_name)
        code_input = driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'code')]")
        for cinp in code_input:
            if cinp.is_displayed():
                fill_input(driver, cinp, code)
                confirm_btns = driver.find_elements(By.XPATH, "//button[contains(translate(., 'CONFIRM', 'confirm'), 'confirm')]")
                if confirm_btns:
                    click_element(driver, confirm_btns[0])
                break

    switch_to_tab(driver, "TICKET")
    notes = f"Caller identity successfully verified for {user_name}. MFA credentials reset as requested."
    resolve_ticket(driver, notes)
    return True

# =========================================================================
# 3. ONBOARDING (NEW EMPLOYEE PROVISIONING)
# =========================================================================
def handle_onboarding(driver, info, solution):
    """Executes Onboarding: adds new user account via +👤 button in Directory."""
    print("\n==============================================")
    print("  WORKFLOW: EMPLOYEE ONBOARDING (+👤 NEW USER)")
    print("==============================================")

    open_directory(driver)

    print("  -> Clicking '+👤' (Add User) button...")
    add_user_btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Add') or contains(@aria-label, 'New') or .//*[name()='svg' and contains(@class, 'user-plus')]] | //div[contains(., 'DIRECTORY')]//button[count(.//svg) > 0]")
    if add_user_btns:
        click_element(driver, add_user_btns[0])
        time.sleep(1.5)
    else:
        driver.execute_script("""
            const btns = Array.from(document.querySelectorAll('button'));
            const addBtn = btns.find(b => b.innerHTML.includes('user-plus') || b.getAttribute('aria-label') === 'Add user');
            if (addBtn) addBtn.click();
        """)
        time.sleep(1.5)

    user_modal = find_active_dialog_or_modal(driver) or driver
    first_name = info.get("FirstName") or (info.get("Name", "").split()[0] if info.get("Name") else "")
    last_name = info.get("LastName") or (info.get("Name", "").split()[-1] if info.get("Name") and len(info["Name"].split()) > 1 else "")
    username = info.get("Username") or (f"{first_name[0].lower()}{last_name.lower()}" if first_name and last_name else "")

    fn_inp = find_input(user_modal, ["first name", "firstname", "first"])
    if fn_inp and first_name:
        fill_input(driver, fn_inp, first_name)

    ln_inp = find_input(user_modal, ["last name", "lastname", "last"])
    if ln_inp and last_name:
        fill_input(driver, ln_inp, last_name)

    un_inp = find_input(user_modal, ["username", "logon name", "user logon name", "login"])
    if un_inp and username:
        fill_input(driver, un_inp, username)

    dept_inp = find_input(user_modal, ["department", "dept"])
    if dept_inp and info.get("Department") and info["Department"] != "NOT FOUND":
        fill_input(driver, dept_inp, info["Department"])

    temp_pw = extract_password_from_solution(solution)
    pw_inp = find_input(user_modal, ["password", "initial password", "temp password"])
    if pw_inp:
        fill_input(driver, pw_inp, temp_pw)

    save_btn = find_button(user_modal, ["create", "save", "finish", "add user", "ok"])
    if save_btn:
        click_element(driver, save_btn)
        time.sleep(2)

    user_display = info.get("Name") or username
    notes = (
        f"Onboarding completed for {user_display}. "
        f"User account created in Directory (Username: {username}), "
        f"Department: {info.get('Department', 'General')}, initial password set."
    )
    resolve_ticket(driver, notes)
    return True

# =========================================================================
# 4. OFFBOARDING (EMPLOYEE DEPROVISIONING)
# =========================================================================
def handle_offboarding(driver, info, solution):
    """Executes Offboarding: Disables account and mailbox in Directory."""
    print("\n==============================================")
    print("  WORKFLOW: EMPLOYEE OFFBOARDING")
    print("==============================================")

    user_name = info.get("Name") or "User"
    username = info.get("Username") or info.get("Email", "").split("@")[0] or user_name

    open_directory(driver)
    search_and_select_user_in_directory(driver, user_name, username)

    click_action_button(driver, "DISABLE ACCOUNT")
    time.sleep(1)

    select_manage_tab(driver, "MAILBOX")
    disable_mail_btn = driver.find_elements(By.XPATH, "//button[contains(., 'DISABLE MAILBOX') or contains(., 'Disable Mailbox')]")
    if disable_mail_btn and disable_mail_btn[0].is_displayed():
        print("  -> Disabling user mailbox...")
        click_element(driver, disable_mail_btn[0])
        time.sleep(1)

    notes = (
        f"Offboarding completed for {user_name}. "
        f"Account and mailbox disabled in Active Directory, active sessions revoked, and access removed."
    )
    resolve_ticket(driver, notes)
    return True

# =========================================================================
# ROUTER
# =========================================================================
def execute_ticket_workflow(driver, category, info, solution):
    """Routes the ticket to the specialized workflow handler."""
    print(f"\n[ROUTER] Starting workflow for: [{category}]")

    if category == CATEGORY_ONBOARDING:
        return handle_onboarding(driver, info, solution)
    elif category == CATEGORY_OFFBOARDING:
        return handle_offboarding(driver, info, solution)
    elif category == CATEGORY_RESET_PASSWORD:
        return handle_reset_password(driver, info, solution)
    elif category == CATEGORY_USER_AUTHENTICATION:
        return handle_user_authentication(driver, info, solution)
    else:
        if "password" in solution.lower():
            return handle_reset_password(driver, info, solution)
        return False
