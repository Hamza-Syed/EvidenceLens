"""Live production frontend -> PDF upload -> retrieval -> semantic verifier smoke test."""
import json

import httpx2
import pymupdf


def main() -> None:
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 72), "The trial enrolled 312 participants.")
        pdf.new_page().insert_text((72, 72), "The intervention did not significantly reduce blood pressure.")
        content = pdf.tobytes()
    with httpx2.Client(base_url="http://127.0.0.1:3000", timeout=180) as client:
        response = client.get("/")
        assert response.status_code == 200 and "Evidence-grounded verification" in response.text
        response = client.post("/api/documents", files={"files": ("verification-smoke.pdf", content, "application/pdf")})
        assert response.status_code == 201, response.text
        document_id = response.json()["documents"][0]["id"]
        cases = [
            ("More than 300 people participated in the trial.", "supported", 1),
            ("The intervention significantly reduced blood pressure.", "contradicted", 2),
            ("Jupiter has ninety-five moons.", "insufficient_evidence", None),
        ]
        for claim, expected, page in cases:
            response = client.post("/api/verifications", json={"text": claim, "document_ids": [document_id]})
            assert response.status_code == 200, response.text
            result = response.json()["results"][0]
            assert result["classification"] == expected, result
            if page is not None:
                assert result["evidence"][0]["page_number"] == page
                assert result["evidence"][0]["document_name"] == "verification-smoke.pdf"
            print(json.dumps(result), flush=True)
    print("Live semantic support, contradiction, and abstention passed.", flush=True)


if __name__ == "__main__":
    main()
