import logging
# Suppress Presidio verbosity
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

from sentinelguard import SentinelGuard

guard = SentinelGuard.minimal()

text = "My phone number is 555-0199 and my email is test@example.com"
result = guard.scan_prompt(text)

print("\n--- SCAN RESULTS ---")
print("Original Text:", text)
print("Is Valid:", result.is_valid)

if not result.is_valid:
    print("Failed Scanners:", result.failed_scanners)
    print("Risk Level:", result.highest_risk.value)
else:
    print("Status: Prompt passed all security checks!")
