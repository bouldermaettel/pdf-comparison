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

## Docker Compose setup

This setup runs frontend and backend in separate containers on the same Docker network.

```bash
cd /home/smc-dev/python-projects/pdf-comparison
docker compose up --build
```

Then open:

- Frontend: `http://localhost:8080`
- Backend health: `http://localhost:8080/api/health`

Stop containers:

```bash
docker compose down
```

Notes:

- Frontend container uses Nginx and proxies `/api/*` to backend service `backend:8000`.
- Backend container runs `uvicorn app:app` on port 8000 (inside Docker network).

## Azure infra (Container Apps)

The `infra/` folder contains a Bicep template for deploying this app to Azure Container Apps.

Deploy command:

```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file infra/main.bicep \
  --parameters infra/parameters.json
```

Before deploying:

- Set `containerImage` in `infra/parameters.json` to your pushed image.
- If using a private registry, fill `registryServer`, `registryUsername`, and `registryPassword`.
- Keep secrets out of source control; use secure parameter handling in CI/CD for production.

## Windows portable build (USB-friendly, no installer)

This project can be shipped as a portable folder that runs on Windows without installing Python on the target machine.

### Build on a Windows machine

From a regular Windows terminal in the project root:

```bat
build_portable.bat
```

This script will:

- build the frontend (`frontend/dist`),
- package the backend and Python runtime via PyInstaller,
- produce the portable output in `dist\\pdf_matcher`,
- copy `run.bat` into the portable folder.

### Ship on USB

Copy the entire `dist\\pdf_matcher` folder to the memory stick.

On the target Windows machine, open that folder and run:

```bat
run.bat
```

The launcher starts the local server (`127.0.0.1:8000`) and opens the app in the default browser.

### Portable notes

- No installer is required.
- If SmartScreen or antivirus warns about unsigned binaries, this is common for self-built executables.
- For development mode, you can still run FastAPI + Vite separately as documented above.

## GitHub Actions build (Windows artifact)

If your local Windows machine cannot build directly, you can use GitHub Actions to build on a Windows runner and download a ready-to-copy zip.

1. Push this repository to GitHub.
2. Open the `Actions` tab.
3. Run workflow `Build Portable Windows Artifact` manually.
4. After completion, download artifact `portable-windows-pdf-matcher`.
5. Extract the zip and copy the `pdf_matcher` folder to your USB stick.
6. Run `run.bat` inside that folder on the target Windows machine.

## Notes

- The extractor is designed to be generic, but it works best when the source PDF contains an actual table with a recognizable header row.
- If a PDF uses unusual layouting and the column cannot be found, try a different column identifier or a stricter value regex.
- The React app proxies `/api/*` requests to the FastAPI backend during development.
