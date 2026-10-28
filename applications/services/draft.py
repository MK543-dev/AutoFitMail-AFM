import json

from resume_gen.services.writer import WriterError, generate_text

EMAIL_SYSTEM = (
    'Act as a professional job application email writer. You write ONE concise email that applies '
    'to ONE job, based on the job description (JD) and the candidate resume. Rules: '
    '1) Analyze the JD (skills, responsibilities, ATS keywords) and the RESUME_JSON; find the '
    'strongest overlaps and pick the 1-2 most relevant projects or achievements. '
    '2) Never invent qualifications, experience, achievements or skills that the resume does not '
    'support. '
    '3) Structure: paragraph 1 = the role applied for and why the candidate fits; paragraph 2 = 1-2 '
    'relevant projects/skills connected to the JD; paragraph 3 = location/availability if relevant, '
    'a polite ask to consider the application and willingness to discuss it. End with a sign-off: '
    'full name, phone, email and links from the resume. '
    '4) 120-180 words, professional, confident, natural, human. Personalize for the role and company. '
    '5) Use JD keywords naturally; no keyword stuffing; do not copy whole sentences from the JD or '
    'the resume. '
    '6) Avoid generic openings like "I am writing to express my interest"; never exaggerate; omit '
    'missing information instead of inventing it. '
    '7) Follow any application instructions in the JD (required subject line or reference number). '
    '8) Return ONLY valid JSON, no markdown: {"subject": "...", "body": "..."}. The subject is the '
    'one the JD requires, otherwise "Application for <role> - <full name>". The body is plain text '
    'with real line breaks (\\n).'
)


def _template_email(user, jd, content):
    name = content.get('name') or user.get_full_name() or user.email
    top_skills = ', '.join(content.get('skills', [])[:3])
    phone = (content.get('contact') or {}).get('phone', '')
    subject = f'Application for {jd.title} - {name}'
    skill_sentence = (
        f'My resume is attached; it highlights my experience with {top_skills}.'
        if top_skills else
        'My resume is attached for your consideration.'
    )
    lines = [
        'Dear Hiring Team,',
        '',
        f'I am writing to apply for the {jd.title} position at {jd.company}. ' + skill_sentence,
        '',
        'Thank you for your time and consideration. I look forward to hearing from you.',
        '',
        'Best regards,',
        name,
    ]
    if phone:
        lines.append(phone)
    return subject, '\n'.join(lines)


def _ai_email(user, jd, content):
    name = content.get('name') or user.get_full_name() or user.email
    prompt = '\n\n'.join([
        'JOB_TITLE: ' + jd.title,
        'COMPANY: ' + jd.company,
        'JOB_DESCRIPTION:\n' + jd.text,
        'CANDIDATE_NAME: ' + name,
        'CANDIDATE_EMAIL: ' + user.email,
        'RESUME_JSON:\n' + json.dumps(content, ensure_ascii=False),
    ])
    raw = generate_text(EMAIL_SYSTEM, prompt, 1200)
    raw = raw[raw.find('{'): raw.rfind('}') + 1]
    data = json.loads(raw)
    subject = (data.get('subject') or '').strip()
    body = (data.get('body') or '').strip()
    if not subject or not body:
        raise ValueError('The AI returned an empty email.')
    return subject[:200], body


def build_email(user, jd, content):
    """AI-written, JD-tailored email; falls back to a clean template offline."""
    if content:
        try:
            return _ai_email(user, jd, content)
        except (WriterError, ValueError, json.JSONDecodeError):
            pass
    return _template_email(user, jd, content)
