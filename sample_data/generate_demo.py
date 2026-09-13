"""Generate the same synthetic PDF served by Try sample. Requires backend install."""
from pathlib import Path

from app.demo import DEMO_NAME, DEMO_TEXT, demo_pdf

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / DEMO_NAME
    target.write_bytes(demo_pdf())
    print(f"Generated {target.name}. Paste:\n{DEMO_TEXT}")
