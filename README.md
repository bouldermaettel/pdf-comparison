# PDF Comparison Utility

This workspace now contains a Python matching engine and a React frontend:

- `pdf_matcher.py`: command-line tool that extracts values from a named column in one PDF and searches them in another PDF.
- `app.py`: FastAPI backend for PDF upload and matching.
- `frontend/`: Vite React + Tailwind frontend.

## Install

```bash
cd /home/smc-dev/python-projects/pdf-comparison
./.venv/bin/pip install -r requirements.txt
```

## CLI usage

```bash
cd /home/smc-dev/python-projects/pdf-comparison
./.venv/bin/python pdf_matcher.py \
  data/20260212_MDR_List_2026_06022026.pdf \
  data/20260212_MDR_DoCs_2026_1c.pdf \
  --column "sales sku" \
  --output data/pdf_match_results.csv
```

Optional flags:

- `--value-pattern`: only keep extracted values that fully match a regex.
- `--contains`: use substring search instead of boundary-aware exact matching.

## Web app usage

```bash
cd /home/smc-dev/python-projects/pdf-comparison
./.venv/bin/pip install -r requirements.txt
cd frontend
npm install
cd ..
./.venv/bin/uvicorn app:app --reload
```

In a second terminal:

```bash
cd /home/smc-dev/python-projects/pdf-comparison/frontend
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Notes

- The extractor is designed to be generic, but it works best when the source PDF contains an actual table with a recognizable header row.
- If a PDF uses unusual layouting and the column cannot be found, try a different column identifier or a stricter value regex.
- The React app proxies `/api/*` requests to the FastAPI backend during development.