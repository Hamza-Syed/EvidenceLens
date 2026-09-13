"""Synthetic demo inputs, never precomputed verification results."""
import pymupdf

DEMO_NAME = "evidencelens-sample.pdf"
DEMO_PAGES = (
    "The trial enrolled 312 participants.",
    "The intervention did not significantly reduce blood pressure.",
    "Participants completed the survey online.",
)
DEMO_TEXT = "\n".join((
    "More than 300 people participated in the trial.",
    "Participants completed the survey online in ten minutes.",
    "The intervention significantly reduced blood pressure.",
    "Jupiter has ninety-five moons.",
))


def demo_pdf() -> bytes:
    with pymupdf.open() as pdf:
        pdf.set_metadata({"title": "EvidenceLens synthetic demonstration", "subject": "Fictional inputs for verification; not research findings"})
        for text in DEMO_PAGES:
            page = pdf.new_page()
            page.insert_textbox((72, 100, 523, 700), text, fontsize=16)
        return pdf.tobytes()
