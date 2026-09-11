"""Generate a small reproducible, two-page PDF without external data."""
from pathlib import Path

import pymupdf

with pymupdf.open() as pdf:
    pdf.new_page().insert_text((72, 72), "The observatory opened in 1998.")
    pdf.new_page().insert_text((72, 72), "The observatory has three telescopes.")
    pdf.save(Path(__file__).with_name("observatory.pdf"))
