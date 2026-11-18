"""DOM utilities for ServiceDesk Simulator.
Provides rock-solid element finders, React input synchronization,
modal handlers, and dedicated helpers for Directory, Tabs, Actions, and Company Chat.
"""
import re, time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from settings import ACTION_DELAY, STEP_DELAY

def scroll_into_view(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    except Exception:
        pass

def click_element(driver, el, pause_after=True):
    """Safely clicks an element using native click or JavaScript fallback."""
    scroll_into_view(driver, el)
    time.sleep(0.3)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    if pause_after:
        time.sleep(ACTION_DELAY)

def fill_input(driver, el, text, clear_first=True):
    """Types text into an input or textarea, syncing React state properly."""
    scroll_into_view(driver, el)
    time.sleep(0.2)
    try:
        el.click()
        if clear_first:
            el.clear()
        el.send_keys(str(text))
    except Exception:
        pass

    # React synthetic event dispatch to ensure state updates
    driver.execute_script("""
        const el = arguments[0], val = arguments[1];
        const isTextArea = el.tagName.toLowerCase() === 'textarea';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
        if (setter) {
            setter.call(el, val);
        } else {
            el.value = val;
        }
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    """, el, str(text))
    time.sleep(0.5)

def set_checkbox(driver, checkbox_el, checked=True):
    """Sets a checkbox to checked or unchecked, updating React state."""
    scroll_into_view(driver, checkbox_el)
    current = checkbox_el.is_selected()
    if current != checked:
        try:
            checkbox_el.click()
        except Exception:
            driver.execute_script("""
                const el = arguments[0], target = arguments[1];
                el.checked = target;
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('input', {bubbles: true}));
            """, checkbox_el, checked)
    time.sleep(0.4)

def find_button(driver, text_candidates, parent=None, timeout=2):
    """Finds a button matching candidate text.
    Uses strict exact match first, then word-boundary match, to avoid substring errors.
    """
    root = parent or driver
    candidates = [c.lower().strip() for c in text_candidates]

    buttons = root.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], input[type='button'], input[type='submit'], div[role='button']")

    # Pass 1: Exact match
    for b in buttons:
        try:
            if not b.is_displayed():
                continue
            b_text = (b.text or b.get_attribute("value") or b.get_attribute("aria-label") or "").strip().lower()
            for cand in candidates:
                if b_text == cand:
                    return b
        except Exception:
            continue

    # Pass 2: Word boundary regex match (e.g. \bdirectory\b)
    for b in buttons:
        try:
            if not b.is_displayed():
                continue
            b_text = (b.text or b.get_attribute("value") or b.get_attribute("aria-label") or "").strip().lower()
            for cand in candidates:
                if cand in ("ad", "x", "ok", "go") and b_text != cand:
                    continue
                if re.search(rf"\b{re.escape(cand)}\b", b_text, re.IGNORECASE):
                    return b
        except Exception:
            continue

    # Pass 3: Safe substring match for longer phrases (>= 5 chars)
    for b in buttons:
        try:
            if not b.is_displayed():
                continue
            b_text = (b.text or b.get_attribute("value") or b.get_attribute("aria-label") or "").strip().lower()
            for cand in candidates:
                if len(cand) >= 5 and cand in b_text:
                    return b
        except Exception:
            continue

    return None

def click_button_if_present(driver, text_candidates, parent=None):
    btn = find_button(driver, text_candidates, parent=parent)
    if btn:
        print(f"  -> Clicking '{text_candidates[0]}'...")
        click_element(driver, btn)
        return True
    return False

def find_input(driver, label_candidates, parent=None):
    """Finds an input or textarea matching label, placeholder, name, or id."""
    root = parent or driver
    candidates = [c.lower().strip() for c in label_candidates]

    inputs = root.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), textarea")
    for inp in inputs:
        try:
            if not inp.is_displayed():
                continue
            ph = (inp.get_attribute("placeholder") or "").lower()
            name = (inp.get_attribute("name") or "").lower()
            aria = (inp.get_attribute("aria-label") or "").lower()
            id_attr = (inp.get_attribute("id") or "").lower()
            combined = f"{ph} {name} {aria} {id_attr}"
            for cand in candidates:
                if cand in combined:
                    return inp
        except Exception:
            continue

    # Search by associated label text
    labels = root.find_elements(By.TAG_NAME, "label")
    for lbl in labels:
        try:
            if not lbl.is_displayed():
                continue
            lbl_text = lbl.text.strip().lower()
            for cand in candidates:
                if cand in lbl_text:
                    for_id = lbl.get_attribute("for")
                    if for_id:
                        matched = root.find_elements(By.ID, for_id)
                        if matched and matched[0].is_displayed():
                            return matched[0]
                    nested = lbl.find_elements(By.CSS_SELECTOR, "input, textarea")
                    if nested and nested[0].is_displayed():
                        return nested[0]
        except Exception:
            continue

    return None

def find_checkbox_by_label(driver, label_candidates, parent=None):
    """Finds a checkbox element matching label or nearby text."""
    root = parent or driver
    candidates = [c.lower().strip() for c in label_candidates]

    labels = root.find_elements(By.TAG_NAME, "label")
    for lbl in labels:
        try:
            if not lbl.is_displayed():
                continue
            lbl_text = lbl.text.strip().lower()
            for cand in candidates:
                if cand in lbl_text:
                    for_id = lbl.get_attribute("for")
                    if for_id:
                        matched = root.find_elements(By.ID, for_id)
                        if matched and matched[0].is_displayed() and matched[0].get_attribute("type") == "checkbox":
                            return matched[0]
                    nested = lbl.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                    if nested and nested[0].is_displayed():
                        return nested[0]
        except Exception:
            continue

    checkboxes = root.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    for cb in checkboxes:
        try:
            if not cb.is_displayed():
                continue
            aria = (cb.get_attribute("aria-label") or "").lower()
            name = (cb.get_attribute("name") or "").lower()
            id_attr = (cb.get_attribute("id") or "").lower()
            combined = f"{aria} {name} {id_attr}"
            for cand in candidates:
                if cand in combined:
                    return cb
        except Exception:
            continue

    return None

def find_active_dialog_or_modal(driver):
    selectors = [
        "[role='dialog']",
        ".modal",
        "[class*='modal']",
        "[class*='dialog']",
        "[class*='popup']",
        "[class*='drawer']",
    ]
    for sel in selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try:
                if el.is_displayed() and el.size["height"] > 50 and el.size["width"] > 100:
                    return el
            except Exception:
                continue
    return None

# =========================================================================
# DEDICATED SERVICEDESK SIMULATOR NAVIGATION HELPERS
# =========================================================================

def switch_to_tab(driver, tab_name):
    """Switches between top-level tabs like 'TICKET', 'AD', or closes with 'X'."""
    tab_name = tab_name.upper().strip()
    tabs = driver.find_elements(By.XPATH, f"//button[normalize-space()='{tab_name}'] | //a[normalize-space()='{tab_name}']")
    for t in tabs:
        try:
            if t.is_displayed():
                print(f"  -> Switching to tab [{tab_name}]...")
                click_element(driver, t)
                time.sleep(STEP_DELAY)
                return True
        except Exception:
            continue
    return False

def close_company_chat_if_open(driver):
    """Closes Company Chat panel if it is currently open on the right."""
    try:
        chat_headings = driver.find_elements(By.XPATH, "//*[normalize-space()='Company Chat']")
        if any(h.is_displayed() for h in chat_headings):
            print("  -> Closing open Company Chat panel to focus on Directory...")
            # Look for close button '✕' or '×' inside chat panel
            close_btns = driver.find_elements(By.XPATH, "//div[contains(., 'Company Chat')]//button[contains(., '✕') or contains(., '×') or .//*[name()='svg']] | //button[contains(@aria-label, 'close chat') or contains(@aria-label, 'Close chat')]")
            for cb in close_btns:
                if cb.is_displayed():
                    click_element(driver, cb)
                    time.sleep(1)
                    return True

            # Fallback: click chat toggle button in header
            driver.execute_script("""
                const btns = Array.from(document.querySelectorAll('header button, nav button'));
                const chatBtn = btns.find(b => {
                    const txt = (b.innerText || b.getAttribute('aria-label') || '').toLowerCase();
                    return txt.includes('chat') || b.innerHTML.includes('chat') || b.innerHTML.includes('message');
                });
                if (chatBtn) chatBtn.click();
            """)
            time.sleep(1)
            return True
    except Exception:
        pass
    return False

def open_directory(driver):
    """Opens Tools -> Directory with complete multi-layered fallbacks."""
    print("  -> Navigating to Tools -> Directory...")

    # 1. Close Company Chat if open so header and page are full-width
    close_company_chat_if_open(driver)

    # 2. Check if [AD] tab is already present in the top-right tab bar
    if switch_to_tab(driver, "AD"):
        print("  -> Switched directly to [AD] tab.")
        return True

    # 3. Check if already on Directory view
    dir_headings = driver.find_elements(By.XPATH, "//h1[contains(., 'DIRECTORY')] | //h2[contains(., 'DIRECTORY')] | //div[contains(text(), 'ALL USERS')]")
    if any(h.is_displayed() for h in dir_headings):
        print("  -> Directory is already open.")
        return True

    # 4. Click 'TOOLS' in header (by text, or wrench icon, or button position)
    clicked_tools = False

    # 4a. By text
    tools_btns = driver.find_elements(By.XPATH, "//header//button[contains(., 'TOOLS') or contains(., 'Tools')] | //nav//button[contains(., 'TOOLS') or contains(., 'Tools')]")
    for b in tools_btns:
        if b.is_displayed():
            print("  -> Clicking 'TOOLS' button in header...")
            click_element(driver, b)
            clicked_tools = True
            break

    # 4b. By wrench icon or position next to MODULES
    if not clicked_tools:
        print("  -> Clicking 'TOOLS' button by wrench icon / position...")
        res = driver.execute_script("""
            const header = document.querySelector('header') || document.querySelector('nav') || document;
            const buttons = Array.from(header.querySelectorAll('button'));
            
            // Look for button containing 'tools' or wrench SVG
            let toolBtn = buttons.find(b => {
                const text = (b.innerText || '').toUpperCase();
                const aria = (b.getAttribute('aria-label') || '').toUpperCase();
                const html = b.innerHTML.toLowerCase();
                return text === 'TOOLS' || aria.includes('TOOL') || html.includes('wrench') || html.includes('tool');
            });
            
            // Fallback: button right after MODULES
            if (!toolBtn) {
                const modIdx = buttons.findIndex(b => (b.innerText || '').toUpperCase().includes('MODULES'));
                if (modIdx !== -1 && buttons[modIdx + 1]) {
                    toolBtn = buttons[modIdx + 1];
                }
            }

            if (toolBtn) {
                toolBtn.click();
                return true;
            }
            return false;
        """)
        clicked_tools = bool(res)
        time.sleep(1)

    # 5. Click 'Directory' from dropdown menu (under INFRASTRUCTURE)
    time.sleep(1)
    dir_clicked = False
    dir_items = driver.find_elements(By.XPATH, "//div[normalize-space()='Directory'] | //button[normalize-space()='Directory'] | //span[normalize-space()='Directory'] | //a[normalize-space()='Directory']")
    for item in dir_items:
        try:
            if item.is_displayed():
                print("  -> Clicking 'Directory' from Tools dropdown...")
                click_element(driver, item)
                dir_clicked = True
                time.sleep(STEP_DELAY)
                break
        except Exception:
            continue

    if not dir_clicked:
        # JS fallback click
        driver.execute_script("""
            const items = Array.from(document.querySelectorAll('div, button, a, span'));
            const dirItem = items.find(el => {
                const t = (el.innerText || '').trim();
                return t === 'Directory' && el.offsetParent !== null;
            });
            if (dirItem) dirItem.click();
        """)
        time.sleep(STEP_DELAY)

    # 6. Verify [AD] tab or Directory view
    if switch_to_tab(driver, "AD"):
        return True

    dir_headings = driver.find_elements(By.XPATH, "//h1[contains(., 'DIRECTORY')] | //h2[contains(., 'DIRECTORY')] | //div[contains(text(), 'ALL USERS')]")
    return any(h.is_displayed() for h in dir_headings)

def open_company_chat(driver):
    """Opens Company Chat by clicking the speech bubble icon in header."""
    print("  -> Opening Company Chat...")
    # Check if already open
    chat_headings = driver.find_elements(By.XPATH, "//*[normalize-space()='Company Chat']")
    if any(h.is_displayed() for h in chat_headings):
        print("  -> Company Chat is already open.")
        return True

    # Click chat bubble in header
    driver.execute_script("""
        const header = document.querySelector('header') || document.querySelector('nav') || document;
        const btns = Array.from(header.querySelectorAll('button, a'));
        const chatBtn = btns.find(b => {
            const txt = (b.innerText || b.getAttribute('aria-label') || '').toLowerCase();
            const html = b.innerHTML.toLowerCase();
            return txt.includes('chat') || html.includes('chat') || html.includes('message');
        });
        if (chatBtn) {
            chatBtn.click();
        } else {
            // Find 4th or 5th button in header
            const candidates = buttons.filter(b => b.querySelector('svg'));
            if (candidates.length >= 3) candidates[2].click();
        }
    """)
    time.sleep(2)
    return True
