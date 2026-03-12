from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from pdf_matcher import extract_source_values, results_to_csv_text, results_to_rows, search_values_in_pdf


app = FastAPI(title="PDF Value Matcher API", version="1.0.0")

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", BASE_DIR / "frontend" / "dist"))
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
FRONTEND_AVAILABLE = FRONTEND_INDEX.exists()

if not FRONTEND_AVAILABLE:
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

if FRONTEND_DIST.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIST)), name="frontend-dist")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> HTMLResponse | FileResponse:
    if FRONTEND_AVAILABLE:
        return FileResponse(str(FRONTEND_INDEX))
    return HTMLResponse(
        "Frontend build not found. Run `npm --prefix frontend run build` for packaged mode or use the Vite dev server.",
        status_code=503,
    )


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


@app.get("/{asset_path:path}", include_in_schema=False)
def spa_fallback(asset_path: str) -> HTMLResponse | FileResponse:
    if asset_path.startswith("api/"):
        return HTMLResponse(status_code=404, content="Not found")

    if FRONTEND_AVAILABLE:
        static_asset = FRONTEND_DIST / asset_path
        if static_asset.is_file():
            return FileResponse(str(static_asset))
        return FileResponse(str(FRONTEND_INDEX))

    return HTMLResponse(status_code=404, content="Not found")


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()