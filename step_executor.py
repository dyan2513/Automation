"""Step-by-step solution executor for ServiceDesk Simulator.
Parses revealed instructions and executes them against Directory, Tabs, Chat, and Ticket views.
"""
import re, time
from dom_utils import (
    click_element, fill_input, set_checkbox, find_button,
    find_input, find_checkbox_by_label, open_directory, switch_to_tab,
    open_company_chat, scroll_into_view
)
from workflows import (
    search_and_select_user_in_directory, select_manage_tab,
    click_action_button, get_otp_from_company_chat,
    send_chat_credentials, resolve_ticket, extract_password_from_solution
)
from settings import ACTION_DELAY

def parse_solution_steps(solution_text):
    """Splits solution text into distinct numbered steps."""
    lines = solution_text.splitlines()
    steps = []
    current_step = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^(?:step\s*)?(\d+)[\.\:\-\)]\s*(.+)$", stripped, re.IGNORECASE)
        if m:
            if current_step:
                steps.append(current_step.strip())
            current_step = m.group(2)
        else:
            if current_step:
                current_step += " " + stripped
            elif any(k in stripped.lower() for k in ("open tools", "search for", "open the", "click", "ask her", "send it")):
                steps.append(stripped)

    if current_step:
        steps.append(current_step.strip())

    return steps

def execute_single_step(driver, step_text, info):
    """Executes a parsed step instruction."""
    step = step_text.strip()
    step_lower = step.lower()
    print(f"\n[EXECUTING STEP]: {step}")

    quotes = re.findall(r"['\"]([^'\"]+)['\"]", step)

    # 1. Open Tools -> Directory
    if "tools" in step_lower and "directory" in step_lower:
        return open_directory(driver)

    # 2. Search for user and click her to select her
    if "search for" in step_lower or "search" in step_lower:
        target = quotes[0] if quotes else (info.get("Username") or info.get("Name"))
        if target:
            return search_and_select_user_in_directory(driver, target)

    # 3. Open specific tab (Authentication, Profile, Groups, Mailbox, Devices, Licenses)
    if "tab" in step_lower:
        for tab in ("AUTHENTICATION", "PROFILE", "GROUPS", "MAILBOX", "DEVICES", "LICENSES"):
            if tab.lower() in step_lower:
                return select_manage_tab(driver, tab)

    # 4. Click Send Verification Code
    if "verification code" in step_lower:
        v_btn = find_button(driver, ["send verification code", "verification code"])
        if v_btn:
            click_element(driver, v_btn)
            time.sleep(2)
            return True

    # 5. Company Chat actions
    if "company chat" in step_lower or "chat" in step_lower:
        user_name = info.get("Name") or "Maria Garcia"
        if "ask" in step_lower or "code" in step_lower or "otp" in step_lower:
            code = get_otp_from_company_chat(driver, user_name)
            code_inp = find_input(driver, ["code", "verification", "enter code"])
            if code_inp and code:
                fill_input(driver, code_inp, code)
                click_action_button(driver, "CONFIRM IDENTITY")
                return True
        elif "send it" in step_lower or "send" in step_lower or "temporary password" in step_lower:
            temp_pw = extract_password_from_solution(step)
            send_chat_credentials(driver, user_name, temp_pw)
            return True

    # 6. Click Reset Password action
    if "reset password" in step_lower:
        return click_action_button(driver, "RESET PASSWORD")

    # 7. Click Disable Account action
    if "disable account" in step_lower or "disable user" in step_lower:
        return click_action_button(driver, "DISABLE ACCOUNT")

    # 8. Resolve ticket
    if "resolve" in step_lower or "close" in step_lower:
        return resolve_ticket(driver, "Resolved in accordance with solution instructions.")

    # Generic quote button click fallback
    if quotes:
        for q in quotes:
            btn = find_button(driver, [q])
            if btn:
                click_element(driver, btn)
                return True

    return False

def execute_steps(driver, solution_text, info):
    steps = parse_solution_steps(solution_text)
    if not steps:
        return False

    print(f"\n=== EXECUTING {len(steps)} SOLUTION STEPS ===")
    success_count = 0
    for i, step in enumerate(steps, 1):
        print(f"\nStep {i}/{len(steps)}: {step}")
        if execute_single_step(driver, step, info):
            success_count += 1
        time.sleep(ACTION_DELAY)

    return success_count > 0
