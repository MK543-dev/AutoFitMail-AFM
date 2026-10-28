import re

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
IGNORE = ('noreply', 'no-reply', 'donotreply')
OPTIONAL_RE = re.compile(r'(nice to have|good to have|preferred|bonus|is a plus|are a plus)', re.I)

FREEMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
    'protonmail.com', 'proton.me', 'rediffmail.com', 'live.com',
}
_EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u27BF\u2B00-\u2BFF\uFE0F\u200d]')
_MARKUP_RE = re.compile(r'[*`_]+')
_LABEL_TITLE_RE = re.compile(r'(?:position|role|job title|hiring for)\s*[:\-]\s*(.+)', re.I)
_LABEL_COMPANY_RE = re.compile(r'company\s*[:\-]\s*(.+)', re.I)
_EMAIL_ANCHOR_RE = re.compile(r'(apply|send|contact|reach|email)', re.I)
_GENERIC_HEADLINE_RE = re.compile(r'(we are hiring|now hiring|urgent|job opening|vacancy|apply now|hiring)', re.I)


def find_email(text):
    for match in EMAIL_RE.findall(text):
        if not any(word in match.lower() for word in IGNORE):
            return match
    return ''


def find_all_emails(text):
    seen = []
    for match in EMAIL_RE.finditer(text):
        email = match.group(0)
        if any(word in email.lower() for word in IGNORE):
            continue
        if email not in seen:
            seen.append(email)
    return seen


def _clean(line):
    line = _EMOJI_RE.sub('', line)
    line = _MARKUP_RE.sub('', line)
    return re.sub(r'\s{2,}', ' ', line).strip(' \t-•·|')


def parse_jd(text):
    """Best-effort extraction from a pasted job post (emojis/markdown ok).

    Returns the role title, company, the apply (To) email and any Cc emails.
    """
    emails = find_all_emails(text)
    apply_email, cc_emails = '', []
    if emails:
        primary = 0
        anchor = _EMAIL_ANCHOR_RE.search(text)
        if anchor:
            best = None
            for i, email in enumerate(emails):
                dist = abs(text.find(email) - anchor.start())
                if best is None or dist < best:
                    best, primary = dist, i
        apply_email = emails[primary]
        cc_emails = [e for e in emails if e != apply_email]

    lines = [ln for ln in (_clean(ln) for ln in text.splitlines()) if ln]

    headline = ''
    for line in lines[:6]:
        if len(re.sub(r'[^A-Za-z]', '', line)) >= 3:
            headline = line
            break
    parts = [p.strip() for p in headline.split('|') if p.strip()]
    parts = [p for p in parts if not _GENERIC_HEADLINE_RE.search(p)]

    title = ''
    label = _LABEL_TITLE_RE.search(text)
    if label:
        title = _clean(label.group(1)).split('|')[0].strip()
    if not title and parts:
        title = parts[0]
    if not title:
        title = headline[:80]

    company = ''
    label = _LABEL_COMPANY_RE.search(text)
    if label:
        company = _clean(label.group(1)).split('|')[0].strip()
    if not company and len(parts) > 1 and parts[-1].lower() != title.lower():
        company = parts[-1]
    if not company and apply_email and '@' in apply_email:
        domain = apply_email.split('@', 1)[1].lower()
        if domain not in FREEMAIL_DOMAINS and '.' in domain:
            company = domain.split('.')[0].capitalize()

    return {
        'title': title[:160],
        'company': company[:160],
        'apply_email': apply_email,
        'cc_emails': cc_emails[:10],
    }


def split_required_optional(jd_text):
    """Text before the first 'nice to have' style marker is required; the rest is optional."""
    m = OPTIONAL_RE.search(jd_text)
    if not m:
        return jd_text, ''
    return jd_text[:m.start()], jd_text[m.start():]
