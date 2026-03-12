from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from pdf_matcher import extract_source_values, results_to_csv_text, results_to_rows, search_values_in_pdf


app = FastAPI(title="PDF Value Matcher API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/match")
async def match_pdfs(
    source_pdf: UploadFile = File(...),
    target_pdf: UploadFile = File(...),
    column_identifier: str = Form(...),
    value_pattern: str = Form(""),
    exact_match: bool = Form(True),
) -> dict[str, object]:
    source_bytes = await source_pdf.read()
    target_bytes = await target_pdf.read()

    source_values = extract_source_values(
        pdf_bytes=source_bytes,
        column_identifier=column_identifier,
        value_pattern=value_pattern or None,
    )
    results = search_values_in_pdf(
        values=source_values,
        target_pdf_bytes=target_bytes,
        exact_match=exact_match,
    )
    result_rows = results_to_rows(results)
    matched_count = sum(1 for row in result_rows if row["found"] == "yes")

    return {
        "summary": {
            "extractedCount": len(source_values),
            "matchedCount": matched_count,
            "unmatchedCount": len(source_values) - matched_count,
        },
        "extractedValues": [{"search_value": item.value, "source_page": item.source_page} for item in source_values],
        "results": result_rows,
        "csv": results_to_csv_text(results),
    }