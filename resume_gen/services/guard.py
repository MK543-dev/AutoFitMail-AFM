import re

from django.conf import settings

from analyzer.services.skills import get_catalog


class GuardError(Exception):
    pass


REQUIRED_KEYS = {'name', 'summary', 'skills', 'experience', 'education'}


def _norm(text):
    # Dots collapse to spaces as well, so "Django." at the end of a sentence
    # still matches "Django"; '+' and '#' are kept so C++ / C# survive.
    return ' ' + re.sub(r'[^a-z0-9+#]+', ' ', str(text).lower()).strip() + ' '


def _flatten(value):
    if isinstance(value, dict):
        return ' '.join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(_flatten(v) for v in value)
    return str(value)


def _words(text):
    return [w for w in re.sub(r'[^a-z0-9+#]+', ' ', str(text).lower()).split() if w]


def _skill_supported(skill, source, jd_source=''):
    """True when the resume - or (by default) the JD - backs this skill.

    The literal canonical name counts, any catalog alias counts, and a phrase
    like "Technical Troubleshooting" counts when the JD mentions its base
    term ("troubleshooting"). Set ALLOW_JD_SKILLS=False to require skills to
    come strictly from the resume (the original doc behaviour).
    """
    norm_skill = _norm(skill)
    if norm_skill in source:
        return True
    allow_jd = bool(jd_source) and getattr(settings, 'ALLOW_JD_SKILLS', True)
    skill_words = _words(skill)
    for info in get_catalog().values():
        terms = [info['name'], *info.get('aliases', [])]
        matches_entry = info['name'].lower() == str(skill).lower() or any(
            _words(t) and len(''.join(_words(t))) >= 3
            and all(word in skill_words for word in _words(t))
            for t in terms
        )
        if matches_entry:
            if any(_norm(t) in source for t in terms):
                return True
            if allow_jd and any(_norm(t) in jd_source for t in terms):
                return True
            return False
    if allow_jd:
        return norm_skill in jd_source
    return False


def check(data, resume_text, jd_text=''):
    missing_keys = REQUIRED_KEYS - set(data)
    if missing_keys:
        raise GuardError(f'Missing keys: {sorted(missing_keys)}')
    source = _norm(resume_text)
    jd_source = _norm(jd_text)
    for skill in data['skills']:
        if not _skill_supported(skill, source, jd_source):
            raise GuardError(f'Skill not found in resume or JD: {skill}')
    for job in data['experience']:
        for field in ('company', 'title'):
            if job.get(field) and _norm(job[field]) not in source:
                raise GuardError(f'{field} not found in original resume: {job[field]}')
    resume_numbers = set(re.findall(r'\d+(?:\.\d+)?', resume_text))
    output_numbers = set(re.findall(r'\d+(?:\.\d+)?', _flatten(data)))
    invented = output_numbers - resume_numbers
    if invented:
        raise GuardError(f'Numbers not in original resume: {sorted(invented)}')
    return True
