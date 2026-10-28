from .jd_utils import split_required_optional
from .skills import extract_skills


def score(resume_text, jd_text):
    required_text, optional_text = split_required_optional(jd_text)
    required = set(extract_skills(required_text))
    optional = set(extract_skills(optional_text)) - required
    have = set(extract_skills(resume_text))
    matched = required & have
    missing = required - have
    pct = round(len(matched) / len(required) * 100, 1) if required else 0.0
    return {
        'score': pct,
        'required': sorted(required),
        'matched': sorted(matched),
        'missing': sorted(missing),
        'optional_missing': sorted(optional - have),
        'resume_skills': sorted(have),
    }
