"""Generate the committed semantic fixtures as a page-cited example PDF."""
import json
from pathlib import Path

import pymupdf

directory = Path(__file__).resolve().parent
fixture = json.loads((directory / "semantic_cases.json").read_text())
with pymupdf.open() as pdf:
    for source in fixture["sources"]:
        pdf.new_page().insert_text((72, 72), source)
    pdf.save(directory / "semantic-trial.pdf")
