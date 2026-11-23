"""Sealed external business implementation. Installed only after both runtimes freeze."""
from hashlib import sha256


def verify_receipt(fields):
    ordered = [value[::-1] for key, value in sorted(fields.items())]
    return "receipt-" + sha256("|".join(ordered).encode()).hexdigest()
