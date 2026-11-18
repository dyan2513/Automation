"""Ticket classification module.
Detects whether a ticket belongs to:
 - Onboarding
 - Offboarding
 - Reset Password
 - User Authentication
"""
import re

CATEGORY_ONBOARDING = "Onboarding"
CATEGORY_OFFBOARDING = "Offboarding"
CATEGORY_RESET_PASSWORD = "Reset Password"
CATEGORY_USER_AUTHENTICATION = "User Authentication"
CATEGORY_GENERAL = "General Support"

ONBOARDING_KEYWORDS = [
    r"\bonboard(?:ing)?\b",
    r"\bnew\s+hire\b",
    r"\bnew\s+employee\b",
    r"\bnew\s+user\b",
    r"\bcreate\s+account\b",
    r"\bcreate\s+user\b",
    r"\bprovision(?:ing)?\b",
    r"\bsetup\s+account\b",
    r"\bnew\s+starter\b",
    r"\bjoiner\b",
    r"\baccount\s+creation\b",
]

OFFBOARDING_KEYWORDS = [
    r"\boffboard(?:ing)?\b",
    r"\bdeparture\b",
    r"\bterminat(?:e|ion)\b",
    r"\bdeprovision(?:ing)?\b",
    r"\bdisable\s+account\b",
    r"\bdisable\s+user\b",
    r"\bleaver\b",
    r"\bexit\b",
    r"\bdeactivat(?:e|ion)\b",
    r"\bresign(?:ation)?\b",
    r"\brevoke\s+access\b",
    r"\bremove\s+account\b",
]

PASSWORD_KEYWORDS = [
    r"\breset\s+password\b",
    r"\bpassword\s+reset\b",
    r"\bforgot\s+password\b",
    r"\bunlock\s+account\b",
    r"\blocked\s+out\b",
    r"\blockout\b",
    r"\bpassword\s+expired\b",
    r"\bchange\s+password\b",
    r"\bbad\s+password\b",
    r"\btemp(?:orary)?\s+password\b",
    r"\bcan(?:'|no)?t\s+log\s*in\b",
]

AUTH_KEYWORDS = [
    r"\bcaller\s+verification\b",
    r"\bverify\s+caller\b",
    r"\bverify\s+identity\b",
    r"\bidentity\s+verification\b",
    r"\buser\s+authentication\b",
    r"\bauthenticat(?:e|ion)\b",
    r"\bmfa\b",
    r"\b2fa\b",
    r"\btwo[- ]factor\b",
    r"\bmulti[- ]factor\b",
    r"\bauthenticator\b",
    r"\bsecurity\s+question(?:s)?\b",
    r"\bverification\s+code\b",
    r"\bidentity\s+check\b",
]

def _score(text, patterns):
    score = 0
    for p in patterns:
        matches = len(re.findall(p, text, re.IGNORECASE))
        score += matches
    return score

def classify_ticket(title="", body="", solution=""):
    """Determines the primary category for a given ticket.
    Returns one of:
      - 'Onboarding'
      - 'Offboarding'
      - 'Reset Password'
      - 'User Authentication'
      - 'General Support'
    """
    combined = f"{title}\n{body}\n{solution}"

    scores = {
        CATEGORY_ONBOARDING: _score(combined, ONBOARDING_KEYWORDS) * 2 + _score(title, ONBOARDING_KEYWORDS) * 3,
        CATEGORY_OFFBOARDING: _score(combined, OFFBOARDING_KEYWORDS) * 2 + _score(title, OFFBOARDING_KEYWORDS) * 3,
        CATEGORY_RESET_PASSWORD: _score(combined, PASSWORD_KEYWORDS) * 2 + _score(title, PASSWORD_KEYWORDS) * 3,
        CATEGORY_USER_AUTHENTICATION: _score(combined, AUTH_KEYWORDS) * 2 + _score(title, AUTH_KEYWORDS) * 3,
    }

    # If password reset also mentions verification, password reset is usually the ultimate action,
    # but verification is an explicit requirement of it.
    best_cat, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score > 0:
        return best_cat

    # Fallback checks on title
    title_lower = title.lower()
    if "onboard" in title_lower or "new" in title_lower:
        return CATEGORY_ONBOARDING
    if "offboard" in title_lower or "terminat" in title_lower or "disable" in title_lower:
        return CATEGORY_OFFBOARDING
    if "password" in title_lower or "unlock" in title_lower:
        return CATEGORY_RESET_PASSWORD
    if "verify" in title_lower or "auth" in title_lower or "mfa" in title_lower:
        return CATEGORY_USER_AUTHENTICATION

    return CATEGORY_GENERAL

def is_target_category(category, target_setting):
    """Checks if a classified category matches the user's TARGET_CATEGORY setting."""
    setting = (target_setting or "ALL").upper().replace(" ", "_")
    if setting in ("ALL", "ANY"):
        return category in (
            CATEGORY_ONBOARDING,
            CATEGORY_OFFBOARDING,
            CATEGORY_RESET_PASSWORD,
            CATEGORY_USER_AUTHENTICATION
        )
    if setting == "ONBOARDING" and category == CATEGORY_ONBOARDING:
        return True
    if setting == "OFFBOARDING" and category == CATEGORY_OFFBOARDING:
        return True
    if setting in ("RESET_PASSWORD", "PASSWORD") and category == CATEGORY_RESET_PASSWORD:
        return True
    if setting in ("USER_AUTHENTICATION", "AUTH", "AUTHENTICATION", "VERIFICATION") and category == CATEGORY_USER_AUTHENTICATION:
        return True
    return False
