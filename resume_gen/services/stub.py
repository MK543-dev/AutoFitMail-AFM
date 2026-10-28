"""Deterministic stand-in for the LLM writer.

Used until ANTHROPIC_API_KEY is configured so the full flow (and the
tests) work locally. It only reuses text that is already in the resume,
so the no-invention guard passes by construction.
"""
import re

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'\+?\d[\d\s().-]{7,}\d')


def _find_phone(text):
    for m in PHONE_RE.finditer(text):
        if sum(ch.isdigit() for ch in m.group(0)) >= 7:
            return m.group(0).strip()
    return ''


def stub_rewrite(resume_text, jd_text):
    from analyzer.services.skills import extract_skills  # local import avoids app-loading cycles

    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    email_m = EMAIL_RE.search(resume_text)
    return {
        'name': lines[0] if lines else '',
        'contact': {
            'email': email_m.group(0) if email_m else '',
            'phone': _find_phone(resume_text),
            'location': '',
            'links': [],
        },
        'summary': ' '.join(lines[:2]),
        'skills': extract_skills(resume_text),
        'experience': [{
            'title': '',
            'company': '',
            'dates': '',
            'bullets': lines[2:7],
        }],
        'education': [],
        'projects': [],
    }
