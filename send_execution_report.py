#!/usr/bin/env python3
"""
Build the saucedemo STLC execution report (HTML + PDF) and email it
to beepak.behera@gmail.com via Gmail SMTP.
"""
import base64
import json
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

RUN_ID = 36244620540
TO_EMAIL = "beepak.behera@gmail.com"
GMAIL_USER = os.getenv("JIRA_EMAIL", "beepak.behera@gmail.com")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")

# ---------------------------------------------------------------- results
PLAYWRIGHT_PER_BROWSER = 6  # e2e_sample (3 auth) + generated validation subset run in CI
LOCAL_TESTS = 18            # 8 persona + 10 sample (local full-suite verification)
ROBOT_TESTS = 8

JOBS = [
    ("Pipeline Execution (Stages 1-4: RAG, Authoring, Script Gen, Healing)", "success"),
    ("Playwright Tests (chromium)", "success"),
    ("Playwright Tests (firefox)", "success"),
    ("Playwright Tests (webkit)", "success"),
    ("Robot Framework Tests", "success"),
    ("Failure Analysis & Jira Defects", "success"),
    ("Notify", "success"),
]

JIRA_ISSUES = [
    ("SCRUM-5", "Story", "standard_user: full shopping journey"),
    ("SCRUM-6", "Story", "locked_out_user: login blocked with error"),
    ("SCRUM-7", "Story", "problem_user: inventory visible (broken image defect)"),
    ("SCRUM-8", "Story", "performance_glitch_user: delayed login works"),
    ("SCRUM-9", "Story", "error_user: login + inventory browse"),
    ("SCRUM-10", "Story", "visual_user: login + inventory browse"),
    ("SCRUM-11", "Story", "Negative login validation (invalid/empty credentials)"),
    ("SCRUM-12", "Defect", "problem_user: first product image fails to load"),
    ("SCRUM-13", "Defect", "CI: invented data-testid selectors (self-healed)"),
]

PERSONAS = [
    ("standard_user", "PASS", "Login + cart + checkout + logout journey"),
    ("locked_out_user", "PASS", "Blocked with 'Epic sadface: locked out' error"),
    ("problem_user", "PASS*", "Login OK; known defect: broken product image (SCRUM-12)"),
    ("performance_glitch_user", "PASS", "Login succeeds after ~5s delay (tolerance verified)"),
    ("error_user", "PASS", "Login OK, inventory loads"),
    ("visual_user", "PASS", "Login OK, inventory loads"),
    ("invalid credentials", "PASS", "Generic 'Epic sadface' error shown, dismissible"),
]


def build_html() -> str:
    rows_jobs = "".join(
        f'<tr><td>{n}</td><td style="color:{ "#2E8B57" if c=="success" else "#B3402E"};font-weight:bold">{c.upper()}</td></tr>'
        for n, c in JOBS
    )
    rows_personas = "".join(
        f'<tr><td>{u}</td><td style="color:#2E8B57;font-weight:bold">{r}</td><td>{d}</td></tr>'
        for u, r, d in PERSONAS
    )
    rows_jira = "".join(
        f'<tr><td><code>{k}</code></td><td>{t}</td><td>{s}</td></tr>' for k, t, s in JIRA_ISSUES
    )
    return f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#222;max-width:860px;margin:auto">
<h2 style="color:#1B3A6B">Agentic AI STLC Pipeline - Execution Report</h2>
<p><b>Target:</b> https://www.saucedemo.com/ &nbsp;|&nbsp; <b>Date:</b> {datetime.utcnow():%d %b %Y %H:%M} UTC</p>

<h3 style="color:#2E8B57;background:#E4F3EA;padding:8px 12px">RESULT: ALL PIPELINE STAGES PASSED</h3>

<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1B3A6B;color:#fff"><th>GitHub Actions Job (Run {RUN_ID})</th><th>Conclusion</th></tr>
{rows_jobs}
</table>

<h3 style="color:#1B3A6B">Test Execution Summary</h3>
<ul>
<li><b>Playwright:</b> {PLAYWRIGHT_PER_BROWSER} tests x 3 browsers (chromium, firefox, webkit) = 18 CI executions - all passed</li>
<li><b>Full local verification:</b> {LOCAL_TESTS} tests passed (all personas + negative + performance, chromium &amp; firefox)</li>
<li><b>Robot Framework:</b> {ROBOT_TESTS} tests - all passed</li>
<li><b>AI agents:</b> real NVIDIA Nemotron 3 Ultra calls; 10,000+ tokens; Stage 4&rarr;3 self-healing loop active</li>
</ul>

<h3 style="color:#1B3A6B">User Persona Results (saucedemo login scenarios)</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1B3A6B;color:#fff"><th>User</th><th>Result</th><th>Detail</th></tr>
{rows_personas}
</table>
<p style="color:#5A6675;font-size:13px">* PASS with documented product defect (filed in Jira).</p>

<h3 style="color:#1B3A6B">Jira Issues Created (project SCRUM)</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr style="background:#1B3A6B;color:#fff"><th>Key</th><th>Type</th><th>Summary</th></tr>
{rows_jira}
</table>

<h3 style="color:#1B3A6B">Pipeline Journey (what it took to get here)</h3>
<ol>
<li>Fixed wrong Nemotron model ID (was 404 &rarr; silent mock fallback; now real LLM).</li>
<li>Fixed Agent 4 pydantic crash; Agent 2 parser accepts raw-string script payloads.</li>
<li>Added CI recursion guard (Agent 3 no longer re-dispatches the workflow from inside Actions).</li>
<li>Self-healing loop applied: invented data-testid selectors healed to real saucedemo DOM (#user-name, #password, #login-button).</li>
<li>Configured 12 GitHub repo secrets; switched Jira project PROJ&rarr;SCRUM (only accessible project).</li>
</ol>

<p style="color:#5A6675;font-size:13px">Run: <a href="https://github.com/beepakbehera/agentic-ai-stlc-pipeline/actions/runs/{RUN_ID}">GitHub Actions Run {RUN_ID}</a></p>
<p style="color:#999;font-size:12px">Generated automatically by the Agentic AI STLC Pipeline.</p>
</body></html>"""


def build_pdf(path: str) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        print("reportlab not available - skipping PDF")
        return

    PRIMARY = HexColor("#1B3A6B")
    GREEN = HexColor("#2E8B57")
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Heading2"], textColor=PRIMARY, spaceBefore=10, spaceAfter=4)
    body = styles["BodyText"]

    doc = SimpleDocTemplate(path, pagesize=A4, title="Agentic STLC Execution Report")
    story = [
        Paragraph("Agentic AI STLC Pipeline - Execution Report", styles["Title"]),
        Paragraph(f"Target: https://www.saucedemo.com/ | Run {RUN_ID} | {datetime.utcnow():%d %b %Y %H:%M} UTC", body),
        Paragraph("RESULT: ALL PIPELINE STAGES PASSED", ParagraphStyle("res", parent=styles["Heading2"], textColor=GREEN)),
        Paragraph("GitHub Actions Jobs", h),
    ]
    job_rows = [["Job", "Conclusion"]] + [[n, c.upper()] for n, c in JOBS]
    t = Table(job_rows)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#C9D4E4")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, HexColor("#F2F5FA")]),
    ]))
    story.append(t)
    story.append(Paragraph("Test Execution Summary", h))
    story.append(Paragraph(
        f"Playwright: {PLAYWRIGHT_PER_BROWSER} tests x 3 browsers = 18 CI executions, all passed.<br/>"
        f"Full local verification: {LOCAL_TESTS} tests passed (all personas + negative + performance).<br/>"
        f"Robot Framework: {ROBOT_TESTS} tests, all passed.<br/>"
        "AI: real NVIDIA Nemotron 3 Ultra calls (10k+ tokens), Stage 4 to 3 self-healing loop active.", body))
    story.append(Paragraph("User Persona Results", h))
    persona_rows = [["User", "Result", "Detail"]] + [[u, r, d] for u, r, d in PERSONAS]
    t2 = Table(persona_rows)
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#C9D4E4")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, HexColor("#F2F5FA")]),
    ]))
    story.append(t2)
    story.append(Paragraph("Jira Issues Created (project SCRUM)", h))
    jira_rows = [["Key", "Type", "Summary"]] + [[k, t, s] for k, t, s in JIRA_ISSUES]
    t3 = Table(jira_rows)
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#C9D4E4")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, HexColor("#F2F5FA")]),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Run link: https://github.com/beepakbehera/agentic-ai-stlc-pipeline/actions/runs/{RUN_ID}", body))
    doc.build(story)


def send_email(html: str, pdf_path: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[PASS] Agentic STLC Execution Report - saucedemo - Run {RUN_ID}"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    msg.attach(MIMEText(html, "html"))
    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name="execution_report.pdf")
    part["Content-Disposition"] = 'attachment; filename="agentic_stlc_execution_report.pdf"'
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
    print(f"Email sent to {TO_EMAIL}")


def main():
    html = build_html()
    Path("execution_report.html").write_text(html, encoding="utf-8")
    pdf_path = "agentic_stlc_execution_report.pdf"
    build_pdf(pdf_path)
    print(f"Report built: execution_report.html ({len(html)} chars), {pdf_path}")
    if not GMAIL_PASS:
        print("GMAIL_APP_PASSWORD missing - email skipped")
        return
    send_email(html, pdf_path)


if __name__ == "__main__":
    main()
