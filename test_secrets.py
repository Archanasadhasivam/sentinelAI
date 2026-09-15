import logging
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
from sentinelguard import SentinelGuard

guard = SentinelGuard.strict()
text = "My AWS key is AKIAIOSFODNN7EXAMPLE"
result = guard.scan_prompt(text)

print("\n--- SECRETS TEST ---")
print("Text:", text)
print("Is Valid:", result.is_valid)
print("Failed Scanners:", result.failed_scanners)
