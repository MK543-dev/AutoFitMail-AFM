import json
import urllib.error
import urllib.request
from urllib.parse import quote

import anthropic
from django.conf import settings

from .guard import GuardError, check
from .stub import stub_rewrite


class WriterError(Exception):
    """The AI provider call failed; the message is safe to show to the user."""


SYSTEM = (
    'Act as an expert resume writer and recruiter. I provide a job description (JD) and the '
    'candidate real resume text; you build ONE tailored, ATS-friendly, one-page resume. '
    'Rules: '
    '1) Analyze the JD: top skills, responsibilities, ATS keywords, qualifications. '
    '2) Match ONLY the candidate real experience - never invent skills, tools, employers, titles, '
    'dates, degrees, certifications, metrics or achievements not in RESUME_TEXT. '
    '3) Reorder and rewrite, never fabricate: foreground what is relevant to this JD, de-emphasize '
    '(do not delete) what is not. Mirror JD keywords only where the resume truly supports them. '
    '4) Bullet structure: Action Verb + Task + Tools/Skills + measurable impact. Use numbers only '
    'when they appear in RESUME_TEXT - a bullet with no honest number beats an invented one. '
    '5) Vary power verbs across categories: Led, Directed, Spearheaded, Managed, Coordinated, '
    'Supervised, Mentored, Guided, Oversaw, Delegated, Facilitated, Orchestrated, Executed, '
    'Achieved, Delivered, Exceeded, Improved, Increased, Boosted, Generated, Enhanced, Accelerated, '
    'Maximized, Reduced, Optimized, Strengthened, Developed, Designed, Formulated, Conceptualized, '
    'Initiated, Planned, Strategized, Launched, Implemented, Established, Built, Created, Analyzed, '
    'Evaluated, Assessed, Investigated, Identified, Diagnosed, Forecasted, Modeled, Interpreted, '
    'Researched, Examined, Collaborated, Communicated, Presented, Negotiated, Partnered, Liaised, '
    'Influenced, Engaged, Organized, Administered, Streamlined, Maintained, Innovated, Revamped, '
    'Reimagined, Redesigned, Pioneered, Transformed, Modernized, Engineered, Expanded, Scaled, '
    'Acquired, Captured, Grew, Penetrated, Monetized. '
    '6) Bullets: 1-2 lines, ATS-friendly, no filler adjectives. Aim for 5-8 strong bullets in total '
    'across experience and projects, at most 3 per entry. '
    '7) Honesty labeling: mark beginner/academic/coursework-level skills as such inside bullets or '
    'the summary (e.g. "Basic/Academic", "Coursework"); in skills[] list only plain skill names. '
    '8) One page: 2-3 line summary; grouped skills; a short headline subtitle for this target role '
    'using only resume-backed skills. '
    '9) The app renders a clean ATS-friendly PDF from your JSON - do NOT output LaTeX or markdown. '
    '10) If the JD is vague or scam-shaped (asks for money, personal ID numbers, no verifiable '
    'company), stay strictly truthful and add nothing beyond the resume. '
    '11) Return ONLY valid JSON, no markdown. Keys: name, headline, contact {email, phone, location, '
    'links[]}, summary, skills[], experience[{title, company, dates, bullets[]}], '
    'education[{degree, school, dates}], projects[{name, bullets[]}], certifications[]. '
    '12) Put the JD-matched skills first in skills[]; write the summary targeted at this role. '
    '13) Extract certifications exactly as the resume states them (name, issuer, score or level - '
    'e.g. "Duolingo English Test (CEFR B2) - 105/160"); never invent any. '
    '14) If the resume shows no work experience, return an empty experience list - project work '
    'belongs in projects[].'
)


def _base_prompt(resume_text, jd_text, matched_skills):
    return '\n\n'.join([
        'RESUME_TEXT:\n' + resume_text,
        'JOB_DESCRIPTION:\n' + jd_text,
        'SKILLS_TO_EMPHASIZE (verified in the resume): ' + ', '.join(matched_skills),
    ])


def _parse_and_check(raw, resume_text, jd_text):
    raw = raw[raw.find('{'): raw.rfind('}') + 1]
    data = json.loads(raw)
    check(data, resume_text, jd_text)
    return data


def _anthropic_call(system_prompt, user_prompt, max_tokens):
    client = anthropic.Anthropic()
    try:
        msg = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
    except anthropic.APIError as exc:
        raise WriterError(str(exc)) from exc
    return ''.join(getattr(block, 'text', '') for block in msg.content)


def _gemini_call(system_prompt, user_prompt, max_tokens, json_mode=False):
    base_url = settings.GEMINI_BASE_URL.rstrip('/')
    url = (
        f'{base_url}/models/{settings.GEMINI_MODEL}:generateContent'
        f'?key={quote(settings.GEMINI_API_KEY)}'
    )
    generation_config = {'maxOutputTokens': max_tokens, 'temperature': 0.2}
    if json_mode:
        generation_config['responseMimeType'] = 'application/json'
    body = json.dumps({
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'contents': [{'role': 'user', 'parts': [{'text': user_prompt}]}],
        'generationConfig': generation_config,
    }).encode('utf-8')
    request = urllib.request.Request(url, data=body, method='POST')
    request.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:400]
        raise WriterError(f'HTTP {exc.code}: {detail}') from exc
    except OSError as exc:
        raise WriterError(f'Connection problem: {exc}') from exc
    candidates = data.get('candidates') or [{}]
    parts = (candidates[0].get('content') or {}).get('parts') or []
    return ''.join(part.get('text', '') for part in parts)


def _provider_ready():
    if settings.LLM_PROVIDER == 'gemini':
        return bool(settings.GEMINI_API_KEY)
    return bool(settings.ANTHROPIC_API_KEY)


def generate_text(system_prompt, user_prompt, max_tokens=1500):
    """Plain-text completion from the configured AI provider."""
    if not _provider_ready():
        raise WriterError('No AI provider is configured.')
    if settings.LLM_PROVIDER == 'gemini':
        return _gemini_call(system_prompt, user_prompt, max_tokens)
    return _anthropic_call(system_prompt, user_prompt, max_tokens)


def rewrite(resume_text, jd_text, matched_skills):
    if not _provider_ready():
        # No key configured yet (local dev): deterministic stub that only
        # reuses resume facts, so the whole flow stays testable.
        return stub_rewrite(resume_text, jd_text)
    base_prompt = _base_prompt(resume_text, jd_text, matched_skills)
    feedback, last_error = '', ''
    for _ in range(2):  # first try + one retry
        if settings.LLM_PROVIDER == 'gemini':
            raw = _gemini_call(SYSTEM, base_prompt + feedback, 3000, json_mode=True)
        else:
            raw = _anthropic_call(SYSTEM, base_prompt + feedback, 3000)
        try:
            return _parse_and_check(raw, resume_text, jd_text)
        except (json.JSONDecodeError, GuardError) as exc:
            last_error = str(exc)
            feedback = (
                '\n\nYour previous answer was rejected: ' + last_error
                + '. Fix it and return JSON only.'
            )
    raise GuardError(last_error)
