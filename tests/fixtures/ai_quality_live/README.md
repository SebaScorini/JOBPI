# Live AI Quality Fixtures

Use this folder to keep reusable real inputs for end-to-end AI validation.

## Layout

- `jobs/` - editable job description samples in `.txt` or `.md`
- `cvs/` - editable CV PDF samples
- `snapshots/` - extracted raw text, cleaned text, structured JSON, and run reports

## Current samples

- Job: Python Engineer at ETHICS CODE
- CVs: Sebastian Scorini Wizenberg backend and full-stack PDFs copied from the workspace

## Run

```powershell
c:/Users/cepita/Desktop/JOBPI/.venv/Scripts/python.exe scripts/run_ai_end_to_end.py
```

You can override the sample set with `--job` and repeated `--cv` arguments.
