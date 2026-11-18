"""Main orchestrator for ServiceDesk Simulator automation.
Handles end-to-end processing for:
 - Onboarding (New Employee Provisioning)
 - Offboarding (Employee Deprovisioning)
 - Reset Password (Password Reset & Account Unlock)
 - User Authentication (Caller Identity Verification & MFA)

Configure target categories and preferences in settings.py.
"""
import sys
from settings import pause, PROCESS_ALL_QUEUE, TARGET_CATEGORY
from step1_open_site import open_site
from step2_login import login
from step3_select_ticket import select_ticket
from step4_assign_ticket import assign_ticket
from step5_read_and_reveal import read_and_reveal
from step6_ai_agent import run_agent

def process_single_ticket(driver):
    """Processes one ticket through the full pipeline."""
    # 1. Select and open ticket
    body, title, category = select_ticket(driver, target_category=TARGET_CATEGORY)
    pause(why="ticket opened")

    # 2. Assign ticket to technician
    assign_ticket(driver)
    pause(why="ticket assigned")

    # 3. Read requester details and reveal solution steps
    info, solution, final_category = read_and_reveal(driver)
    pause(why="solution revealed and read")

    # 4. Carry out the workflow (Onboarding, Offboarding, Reset Password, or User Authentication)
    run_agent(driver, info, solution, category=final_category)
    pause(why="workflow executed")

def main():
    print("=" * 60)
    print("   ServiceDesk Simulator - Automated Tier 1 IT Support")
    print("   Supported Workflows:")
    print("     [1] Onboarding (User Creation, Groups, Credentials)")
    print("     [2] Offboarding (Account Disabling, Access Revocation)")
    print("     [3] Reset Password (AD Password Reset & Unlock)")
    print("     [4] User Authentication (Caller Verification & MFA)")
    print(f"   Target Filter: {TARGET_CATEGORY}")
    print("=" * 60)

    driver = open_site()
    try:
        pause(why="site loaded")
        login(driver)
        pause(why="after login")

        if PROCESS_ALL_QUEUE:
            print("\n[MODE] Continuous Queue Processing enabled.")
            processed = 0
            while True:
                try:
                    process_single_ticket(driver)
                    processed += 1
                    print(f"\nCompleted {processed} ticket(s). Returning to ticket queue...")
                except KeyboardInterrupt:
                    print("\nProcessing stopped by user.")
                    break
                except Exception as e:
                    print(f"\nError processing ticket: {e}")
                    ans = input("Continue to next ticket? (y/n): ")
                    if ans.lower() != 'y':
                        break
        else:
            process_single_ticket(driver)

    except KeyboardInterrupt:
        print("\nAborted by user.")
    except Exception as e:
        print(f"\nEncountered error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to close browser...")
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
