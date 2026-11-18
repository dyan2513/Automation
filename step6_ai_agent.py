"""Step 6: Carries out the ticket resolution.
Prioritizes specialized domain workflows (Onboarding, Offboarding, Reset Password, User Authentication),
falls back to the step-by-step executor, and supports Ollama AI if enabled.
"""
import json, re, time, urllib.request
from settings import pause, STEP_DELAY, ACTION_DELAY, USE_OLLAMA_IF_AVAILABLE, OLLAMA_MODEL, OLLAMA_URL
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from ticket_classifier import classify_ticket
from workflows import execute_ticket_workflow
from step_executor import execute_steps

MAX_ACTIONS = 15

COLLECT_JS = """
const sel = 'button, a[href], input, textarea, select, [role="button"]';
const out = []; let id = 0;
document.querySelectorAll('[data-ai-id]').forEach(e => e.removeAttribute('data-ai-id'));
for (const el of document.querySelectorAll(sel)) {
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0 || el.disabled) continue;
  el.setAttribute('data-ai-id', id);
  out.push({id: id, tag: el.tagName.toLowerCase(), type: el.type || '',
            text: (el.innerText || el.value || '').trim().slice(0, 60),
            label: el.getAttribute('aria-label') || el.placeholder || el.name || '',
            options: el.tagName === 'SELECT' ? [...el.options].map(o => o.text) : undefined});
  id++;
}
return out;
"""

SYSTEM_PROMPT = """You are an IT technician on ServiceDesk Simulator.
Follow the revealed solution steps:
- Use Tools -> Directory to search for users, create users (+👤), or disable accounts.
- Use Authentication tab to send verification code.
- Use Company Chat (header speech bubble) to retrieve codes or send temporary passwords.
- Switch between TICKET and AD using top-right tabs.
- Resolve ticket once complete.

Reply with ONE JSON object:
  {"action": "click", "id": <number>}
  {"action": "type", "id": <number>, "text": "<text to type>"}
  {"action": "select", "id": <number>, "option": "<option text>"}
  {"action": "done", "summary": "<what you did>"}
"""

def is_ollama_available():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def ask_ollama(messages):
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["message"]["content"]

def parse_action(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON object in AI reply: " + text[:100])
    return json.loads(m.group(0))

def run_action(driver, act):
    if act["action"] == "done":
        return
    el = driver.find_element(By.CSS_SELECTOR, f'[data-ai-id="{int(act["id"])}"]')
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    if act["action"] == "click":
        driver.execute_script("arguments[0].click();", el)
    elif act["action"] == "type":
        el.clear()
        el.send_keys(str(act["text"]))
    elif act["action"] == "select":
        Select(el).select_by_visible_text(act["option"])

def _page(driver):
    try:
        return driver.find_element(By.TAG_NAME, "main").text
    except Exception:
        return driver.find_element(By.TAG_NAME, "body").text

def run_agent(driver, info, solution, category=None):
    if not category:
        category = classify_ticket(body=_page(driver), solution=solution)

    print(f"\n==========================================")
    print(f"   EXECUTING WORKFLOW FOR: [{category}]")
    print(f"==========================================")

    # 1. Primary: Execute via specialized domain workflow
    try:
        success = execute_ticket_workflow(driver, category, info, solution)
        if success:
            print(f"\n[SUCCESS] Completed {category} workflow.")
            return True
    except Exception as e:
        print(f"  [Notice] Domain workflow error: {e}, falling back to step executor...")

    # 2. Secondary: Execute via parsed solution steps
    try:
        if execute_steps(driver, solution, info):
            print(f"\n[SUCCESS] Completed {category} via step executor.")
            return True
    except Exception as e:
        print(f"  [Notice] Step executor error: {e}")

    # 3. Tertiary: Local Ollama AI fallback if running
    if USE_OLLAMA_IF_AVAILABLE and is_ollama_available():
        print("\nEngaging Ollama AI agent...")
        history, messages = [], [{"role": "system", "content": SYSTEM_PROMPT}]
        for n in range(1, MAX_ACTIONS + 1):
            controls = driver.execute_script(COLLECT_JS)
            prompt = (
                f"CATEGORY: {category}\nUSER: {json.dumps(info)}\nSOLUTION:\n{solution[:1500]}\n\n"
                f"ACTIONS DONE: {json.dumps(history)}\n\nCONTROLS:\n{json.dumps(controls)}"
            )
            try:
                raw = ask_ollama(messages + [{"role": "user", "content": prompt}])
                act = parse_action(raw)
                print(f"[{n}] AI: {act}")
                if act.get("action") == "done":
                    return True
                run_action(driver, act)
                time.sleep(ACTION_DELAY)
                history.append(act)
            except Exception:
                break

    print(f"\n[DONE] Execution finished for ticket.")
    return True

if __name__ == "__main__":
    from step1_open_site import open_site
    from step5_read_and_reveal import read_and_reveal
    d = open_site()
    input("Log in and open a ticket by hand, then press Enter... ")
    info, solution, cat = read_and_reveal(d)
    run_agent(d, info, solution, cat)
    input("Press Enter to close...")
    d.quit()
