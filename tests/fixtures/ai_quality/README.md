# AI Quality Fixtures

Edit these files to change what the AI quality harness evaluates:

- `backend_job.txt` - raw job description
- `cv_backend_strong.txt` - CV with strong evidence for the role
- `cv_backend_weak.txt` - CV with weaker or less relevant evidence

The inspection script in `scripts/inspect_ai_quality.py` reads these files and prints:

- raw input
- preprocessed input
- prompt context sent to the model
- raw model output
- parsed structured output
- final frontend-visible output
