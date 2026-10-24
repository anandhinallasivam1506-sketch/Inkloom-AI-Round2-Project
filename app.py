from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import re
import json
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "inkloom.db"
app = Flask(__name__)
app.secret_key = "change-this-for-production"

DEFAULT_GUIDELINES = {
    "brand_name": "Northstar",
    "tone": "Clear, helpful, confident, and honest",
    "required_terms": "Northstar",
    "avoid_terms": "guaranteed results, best in the world, 100% risk-free, miracle",
    "approved_claims": "Northstar helps teams organise their work.\nNorthstar offers a shared workspace for project updates.",
    "accessibility_note": "Use descriptive link text and meaningful image alt text."
}

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS guidelines (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            brand_name TEXT NOT NULL, tone TEXT NOT NULL,
            required_terms TEXT NOT NULL, avoid_terms TEXT NOT NULL,
            approved_claims TEXT NOT NULL, accessibility_note TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, content TEXT NOT NULL, channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending Approval',
            score INTEGER NOT NULL DEFAULT 100, findings TEXT NOT NULL,
            suggestion TEXT NOT NULL, reviewer_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        row = db.execute("SELECT id FROM guidelines WHERE id=1").fetchone()
        if not row:
            db.execute("""INSERT INTO guidelines
                (id, brand_name, tone, required_terms, avoid_terms, approved_claims, accessibility_note)
                VALUES (1, ?, ?, ?, ?, ?, ?)""", tuple(DEFAULT_GUIDELINES.values()))
        count = db.execute("SELECT COUNT(*) AS n FROM reviews").fetchone()["n"]
        if count == 0:
            sample = ("Welcome to Northstar", "Northstar helps teams organise their work. Our shared workspace keeps project updates in one place.", "Website")
            findings, score, suggestion = analyze_content(sample[1], get_guidelines(db))
            now = datetime.now().isoformat(timespec="minutes")
            db.execute("""INSERT INTO reviews (title, content, channel, status, score, findings, suggestion, created_at, updated_at)
                          VALUES (?, ?, ?, 'Approved', ?, ?, ?, ?, ?)""",
                       (sample[0], sample[1], sample[2], score, findings, suggestion, now, now))

def get_guidelines(db=None):
    owns = db is None
    if owns:
        db = connect()
    row = db.execute("SELECT * FROM guidelines WHERE id=1").fetchone()
    result = dict(row) if row else DEFAULT_GUIDELINES.copy()
    if owns:
        db.close()
    return result

def analyze_content(content, guidelines):
    """Transparent, local rule-based checks; no content is sent to an external AI service."""
    findings = []
    lower = content.lower()
    avoid_terms = [x.strip() for x in guidelines["avoid_terms"].split(",") if x.strip()]
    for term in avoid_terms:
        if term.lower() in lower:
            findings.append({
                "severity": "High",
                "issue": f"Potentially risky claim or wording: “{term}”",
                "why": "This wording appears in the brand's avoid-list and may overpromise or sound untrustworthy.",
                "fix": f"Replace “{term}” with a specific, verifiable description."
            })
    approved_claims = [x.strip() for x in guidelines["approved_claims"].splitlines() if x.strip()]
    claim_patterns = [
        (r"(?<!\w)\d{1,3}\s?%", "Numeric promotional claim", "Confirm that the percentage is supported by an approved source."),
        (r"\b(always|never|guarantees?|guaranteed|instant|unlimited)\b", "Absolute or guaranteed wording", "Use a qualified, evidence-based statement instead.")
    ]
    for pattern, label, advice in claim_patterns:
        if re.search(pattern, content, re.I):
            findings.append({"severity": "Medium", "issue": label,
                             "why": "Absolute or numeric claims can be misleading if they are not backed by approved evidence.",
                             "fix": advice})
    required = [x.strip() for x in guidelines["required_terms"].split(",") if x.strip()]
    for term in required:
        if term.lower() not in lower:
            findings.append({"severity": "Medium", "issue": f"Required terminology missing: “{term}”",
                             "why": "The term is listed in the approved brand terminology.",
                             "fix": f"Include “{term}” naturally where relevant."})
    if re.search(r"\b(click here|read more)\b", content, re.I):
        findings.append({"severity": "Low", "issue": "Vague link wording",
                         "why": "Link text should describe the destination for accessibility.",
                         "fix": "Replace vague wording with a descriptive link label."})
    if re.search(r"\b(!!!+|amazing|unbelievable|crazy deal)\b", content, re.I):
        findings.append({"severity": "Low", "issue": "Potentially overexcited tone",
                         "why": f"The requested tone is: {guidelines['tone']}. This wording may not match it.",
                         "fix": "Use calm, specific language that matches the brand voice."})
    if len(content.split()) < 8:
        findings.append({"severity": "Low", "issue": "Limited review context",
                         "why": "The content is very short, so some claims or context may be missing.",
                         "fix": "Add enough context for a reviewer to assess the message."})
    score = max(0, 100 - sum(25 if f["severity"] == "High" else 12 if f["severity"] == "Medium" else 5 for f in findings))
    if not findings:
        findings.append({"severity": "Pass", "issue": "No configured rule violations found",
                         "why": "The local checks did not detect a match against the current rule set. This is not a guarantee of compliance.",
                         "fix": "Continue with human review before publication."})
    # Conservative suggestion: do not rewrite claims automatically; provide a review-ready draft with obvious risky phrases softened.
    suggestion = content
    for term in avoid_terms:
        suggestion = re.sub(re.escape(term), "a specific, verifiable benefit", suggestion, flags=re.I)
    suggestion = re.sub(r"\b(always|never|guarantees?|guaranteed|instant|unlimited)\b", "can help", suggestion, flags=re.I)
    return json.dumps(findings, ensure_ascii=False), score, suggestion

@app.route("/")
def index():
    with connect() as db:
        reviews = db.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT 6").fetchall()
        stats = {
            "total": db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
            "pending": db.execute("SELECT COUNT(*) FROM reviews WHERE status='Pending Approval'").fetchone()[0],
            "revision": db.execute("SELECT COUNT(*) FROM reviews WHERE status='Needs Revision'").fetchone()[0],
            "approved": db.execute("SELECT COUNT(*) FROM reviews WHERE status='Approved'").fetchone()[0]
        }
    return render_template("index.html", reviews=reviews, stats=stats)

@app.route("/review", methods=["GET", "POST"])
def review():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        channel = request.form.get("channel", "Website").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Please enter both a title and content.", "error")
            return render_template("review.html", form=request.form)
        guidelines = get_guidelines()
        findings, score, suggestion = analyze_content(content, guidelines)
        now = datetime.now().isoformat(timespec="minutes")
        with connect() as db:
            cur = db.execute("""INSERT INTO reviews
                (title, content, channel, status, score, findings, suggestion, created_at, updated_at)
                VALUES (?, ?, ?, 'Pending Approval', ?, ?, ?, ?, ?)""",
                (title, content, channel, score, findings, suggestion, now, now))
            review_id = cur.lastrowid
        flash("Content reviewed and sent to the approval queue.", "success")
        return redirect(url_for("review_detail", review_id=review_id))
    return render_template("review.html", form={})

@app.route("/reviews")
def reviews():
    status = request.args.get("status", "")
    with connect() as db:
        if status:
            rows = db.execute("SELECT * FROM reviews WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    return render_template("reviews.html", reviews=rows, selected_status=status)

@app.route("/review/<int:review_id>", methods=["GET", "POST"])
def review_detail(review_id):
    with connect() as db:
        row = db.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            flash("Review not found.", "error")
            return redirect(url_for("reviews"))
        if request.method == "POST":
            action = request.form.get("action", "")
            note = request.form.get("reviewer_note", "").strip()
            revised_content = request.form.get("revised_content", row["content"]).strip()
            if action not in ["Approved", "Needs Revision", "Pending Approval"]:
                flash("Unknown workflow action.", "error")
                return redirect(url_for("review_detail", review_id=review_id))
            guidelines = get_guidelines(db)
            findings, score, suggestion = analyze_content(revised_content, guidelines)
            now = datetime.now().isoformat(timespec="minutes")
            db.execute("""UPDATE reviews SET content=?, status=?, reviewer_note=?, score=?, findings=?, suggestion=?, updated_at=? WHERE id=?""",
                       (revised_content, action, note, score, findings, suggestion, now, review_id))
            flash(f"Review status updated to {action}.", "success")
            return redirect(url_for("review_detail", review_id=review_id))
    return render_template("review_detail.html", review=row, findings=json.loads(row["findings"]))

@app.route("/guidelines", methods=["GET", "POST"])
def guidelines():
    with connect() as db:
        if request.method == "POST":
            values = {
                "brand_name": request.form.get("brand_name", "").strip() or "My Brand",
                "tone": request.form.get("tone", "").strip(),
                "required_terms": request.form.get("required_terms", "").strip(),
                "avoid_terms": request.form.get("avoid_terms", "").strip(),
                "approved_claims": request.form.get("approved_claims", "").strip(),
                "accessibility_note": request.form.get("accessibility_note", "").strip()
            }
            db.execute("""UPDATE guidelines SET brand_name=?, tone=?, required_terms=?, avoid_terms=?, approved_claims=?, accessibility_note=? WHERE id=1""",
                       tuple(values.values()))
            flash("Brand guidelines saved. New reviews will use these rules.", "success")
            return redirect(url_for("guidelines"))
        data = get_guidelines(db)
    return render_template("guidelines.html", guidelines=data)

@app.route("/insights")
def insights():
    with connect() as db:
        rows = db.execute("SELECT findings, status, score FROM reviews").fetchall()
    counts = {}
    for row in rows:
        for finding in json.loads(row["findings"]):
            if finding["severity"] != "Pass":
                counts[finding["issue"]] = counts.get(finding["issue"], 0) + 1
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    average = round(sum(r["score"] for r in rows) / len(rows)) if rows else 0
    return render_template("insights.html", top=top, average=average, total=len(rows))

@app.route("/health")
def health():
    return {"status": "ok", "app": "Inkloom AI", "analysis": "local rule-based checks"}

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
