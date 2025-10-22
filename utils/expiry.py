# generate_expiry.py (run this once now)
import time
from pathlib import Path

def create_expiry_py(path: Path, hours_from_now: int = 30) -> int:
    """
    Create expiry.py containing EXPIRY_EPOCH constant (epoch seconds).
    Returns the epoch written.
    Example file content:
        EXPIRY_EPOCH = 1760000000
    """
    expiry_seconds = int(time.time()) + hours_from_now * 3600
    # expiry_seconds = int(time.time()) + hours_from_now * 6  # in minutes
    content = f"EXPIRY_EPOCH = {expiry_seconds}\n"
    path.write_text(content)
    return expiry_seconds

p = Path("expiry.py")
epoch = create_expiry_py(p, hours_from_now=24)
print("Created expiry.py with EXPIRY_EPOCH =", epoch)
print("Human time:", __import__("datetime").datetime.utcfromtimestamp(epoch).isoformat() + "Z")
