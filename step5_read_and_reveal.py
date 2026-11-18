"""Step 5: read the user's details, click "I don't know how to fix this",
reveal all solution steps, and categorize the ticket.
"""
import re, time
from settings import pause, STEP_DELAY, ACTION_DELAY
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from ticket_classifier import classify_ticket

FIELDS = [
    "Name", "FirstName", "LastName", "Email", "Username",
    "Department", "Title", "Floor", "EmployeeID", "Manager",
    "Phone", "DOB", "Groups", "Password"
]

ALIASES = {
    "Name": ["Reported by", "Reported By", "Full Name", "User Name", "Username", "Caller", "Requester", "Requested By", "Employee Name", "User", "Name"],
    "Email": ["E-mail", "Email Address", "Email", "UPN", "User Principal Name"],
    "Username": ["Username", "User Name", "User Logon Name", "Logon Name", "Account Name", "SAMAccountName", "Login"],
    "Department": ["Dept", "Department", "Division", "Team"],
    "Title": ["Job Title", "Title", "Position", "Role"],
    "Floor": ["Floor", "Location", "Office", "Building", "Room"],
    "EmployeeID": ["Employee ID", "Emp ID", "ID Number", "Staff ID", "Worker ID", "Badge ID"],
    "Manager": ["Manager", "Supervisor", "Reporting Manager", "Reports To"],
    "Phone": ["Phone", "Phone Number", "Telephone", "Extension", "Ext", "Mobile"],
    "DOB": ["Date of Birth", "DOB", "Birth Date"],
    "Groups": ["Groups", "Security Groups", "Distribution Groups", "Member Of", "Permissions"],
    "Password": ["Password", "Temporary Password", "Temp Password", "Initial Password"],
}

def _lower(text):
    return f'translate({text}, "ABCDEFGHIJKLMNOPQRSTUVWXYZ’", "abcdefghijklmnopqrstuvwxyz\'")'

def _button(snippet):
    return (By.XPATH, f'//button[contains({_lower("normalize-space(.)")}, "{snippet.lower()}")]')

def _visible_buttons(driver, locator):
    return [b for b in driver.find_elements(*locator) if b.is_displayed() and b.is_enabled()]

def page_text(driver):
    return driver.find_element(By.TAG_NAME, "body").text

def extract_user_info(text):
    """Parses ticket text and extracts all user, employee, and account parameters."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    info = {}

    for field, aliases in ALIASES.items():
        for label in aliases:
            for i, line in enumerate(lines):
                m = re.match(rf"^{re.escape(label)}\s*[:\-]\s*(.+)$", line, re.I)
                if m:
                    info[field] = m.group(1).strip()
                    break
                if line.lower() == label.lower() and i + 1 < len(lines):
                    info[field] = lines[i + 1]
                    break
            if field in info:
                break

    # Clean Name if it has email in parentheses (e.g. 'Maria Garcia (mgarcia@servicedesk-simulator.com)')
    if "Name" in info and info["Name"] not in ("NOT FOUND", ""):
        m_paren = re.match(r"^([^\(]+?)(?:\s*\((.+?)\))?$", info["Name"])
        if m_paren:
            clean_name = m_paren.group(1).strip()
            info["Name"] = clean_name
            if m_paren.group(2) and "@" in m_paren.group(2):
                info.setdefault("Email", m_paren.group(2).strip())
                if "Username" not in info or info["Username"] == "NOT FOUND":
                    info["Username"] = m_paren.group(2).strip().split("@")[0]

    # Email pattern fallback
    if "Email" not in info:
        m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
        if m:
            info["Email"] = m.group(0)

    # First and Last Name derivations
    if "Name" in info and info["Name"] not in ("NOT FOUND", ""):
        parts = info["Name"].split()
        if len(parts) >= 2:
            info.setdefault("FirstName", parts[0])
            info.setdefault("LastName", parts[-1])
        elif len(parts) == 1:
            info.setdefault("FirstName", parts[0])
            info.setdefault("LastName", "")

    # Username derivation
    if "Username" not in info or info["Username"] == "NOT FOUND":
        if "Email" in info and "@" in info["Email"]:
            info["Username"] = info["Email"].split("@")[0]
        elif info.get("FirstName") and info.get("LastName"):
            info["Username"] = f"{info['FirstName'][0].lower()}{info['LastName'].lower()}"

    for field in FIELDS:
        info.setdefault(field, "NOT FOUND")

    return info

def click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def read_and_reveal(driver, max_steps=25):
    wait = WebDriverWait(driver, 15)
    time.sleep(ACTION_DELAY)

    # 1. User details
    before = page_text(driver)
    info = extract_user_info(before)
    print("\n=== EXTRACTED TICKET DETAILS ===")
    for k, v in info.items():
        if v != "NOT FOUND":
            print(f"  {k:12}: {v}")

    # 2. Click "I don't know how to fix this" if present
    btn_idk = _button("know how to fix")
    idk_buttons = _visible_buttons(driver, btn_idk)
    if idk_buttons:
        click(driver, idk_buttons[0])
        print("\nClicked: 'I don't know how to fix this'")
        time.sleep(ACTION_DELAY)

    # Optional: If an approach selection appears (e.g. Active Directory vs Remote)
    approach_btn = _button("active directory")
    app_buttons = _visible_buttons(driver, approach_btn)
    if app_buttons:
        print("Selected approach: Active Directory")
        click(driver, app_buttons[0])
        time.sleep(ACTION_DELAY)

    # 3. Reveal next step until complete
    btn_next = _button("reveal next")
    steps = 0
    while steps < max_steps:
        buttons = _visible_buttons(driver, btn_next)
        if not buttons:
            break
        click(driver, buttons[0])
        steps += 1
        print(f"Revealed step {steps}")
        time.sleep(ACTION_DELAY)

    print(f"Done revealing ({steps} click(s)).")

    # 4. Read solution text
    after = page_text(driver)
    solution = after.replace(before, "").strip() or after
    print("\n=== REVEALED SOLUTION ===")
    print(solution[:1500] + ("..." if len(solution) > 1500 else ""))

    # Categorize with full solution context
    ticket_category = classify_ticket(body=after, solution=solution)
    print(f"\nFinal Classified Category: [{ticket_category}]")

    with open("ticket_solution.txt", "w", encoding="utf-8") as f:
        f.write("CATEGORY: " + ticket_category + "\n\n")
        f.write("USER DETAILS\n" + "\n".join(f"{k}: {v}" for k, v in info.items() if v != "NOT FOUND"))
        f.write("\n\nSOLUTION\n" + solution)
        f.write("\n\nFULL PAGE TEXT\n" + after)

    return info, solution, ticket_category

if __name__ == "__main__":
    from step1_open_site import open_site
    d = open_site()
    input("Log in, open a ticket by hand, then press Enter... ")
    read_and_reveal(d)
    input("Press Enter to close...")
    d.quit()
