# Inkloom AI — Brand Governance Platform

A working MVP for reviewing content against configurable brand rules, explaining potential issues, and keeping a human approval workflow.

## Features
- Dashboard with review totals and recent activity
- Brand-guideline editor (brand voice, required terms, avoid-list terms, approved-claim notes)
- Content review for website, social, email, advertising, blog, and internal copy
- Explainable local checks for configured avoid terms, required terminology, absolute/numeric claims, vague link text, and possible tone mismatch
- Suggested draft with conservative wording substitutions
- Review queue with status filters
- Human approval, revision request, reviewer notes, and editable content
- Insights into recurring flagged patterns
- SQLite persistence; local health endpoint at `/health`

## Run locally (Windows / VS Code)
1. Install Python 3.10 or newer.
2. Extract this ZIP and open the `inkloom_ai_project` folder in VS Code.
3. Open Terminal in VS Code.
4. Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` and activate again, or use `\.venv\Scripts\python.exe` directly.
5. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open `http://127.0.0.1:5000` in your browser.

If the `python` command is unavailable, try `py app.py`.

## Demo flow
1. Open **Brand guidelines** and edit the brand name, required terms, avoid-list terms, and tone.
2. Choose **New content review** and paste a test message containing a term from the avoid-list.
3. Inspect the explanation, score, and suggested draft.
4. In the right-side review panel, edit the content and select **Approve content** or **Request revision**.
5. Visit **Governance insights** to see repeated findings.

## Important implementation note
This MVP uses transparent local rule-based checks. It does **not** call an external AI model, send content to a third party, or semantically prove facts. The approved-claims field is stored as reference material; a human must verify whether claims are actually supported. The score is a simple heuristic indicator, not a probability or compliance guarantee.

## Architecture
- Frontend: HTML templates, CSS, responsive layout
- Backend: Python + Flask routes
- Data: SQLite (`inkloom.db`, generated automatically)
- Analysis: local Python regular-expression and terminology rules
- Workflow: Pending Approval → Approved / Needs Revision (with reviewer note)

## Round 2 submission notes
- Project name: Inkloom AI — Brand Governance Platform
- Working project link: deploy the app to a host you control before submitting; a local URL is not public.
- Source repository: create a public GitHub repository and push this folder.
- Updated project PDF: use `Inkloom_AI_Round2_Project_Report.pdf` included in this package.
- Completed features and Round 3 improvements are listed in the project report.
- Disclose that AI assistance was used to scaffold code if your event rules require disclosure, and ensure your team understands and can explain every part. The event rules say only work completed during the official build window is judged; do not misrepresent development history.
