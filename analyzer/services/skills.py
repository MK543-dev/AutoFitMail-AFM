import json
from functools import lru_cache

import spacy
from django.conf import settings
from spacy.matcher import PhraseMatcher


@lru_cache(maxsize=1)
def get_catalog():
    with open(settings.SKILLS_FILE, encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _engine():
    try:
        nlp = spacy.load('en_core_web_sm', exclude=['parser', 'ner', 'lemmatizer'])
    except OSError:
        # PhraseMatcher with attr='LOWER' only needs a tokenizer + vocab,
        # so a blank pipeline works even when the statistical model
        # was not downloaded.
        nlp = spacy.blank('en')
    matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
    for key, info in get_catalog().items():
        terms = {key, info['name'], *info.get('aliases', [])}
        matcher.add(info['name'], [nlp.make_doc(t) for t in terms])
    return nlp, matcher


def extract_skills(text):
    """Return a sorted list of canonical skill names found in the text."""
    if not text:
        return []
    nlp, matcher = _engine()
    doc = nlp.make_doc(text)  # tokenizer only; PhraseMatcher with LOWER needs nothing else
    return sorted({nlp.vocab.strings[match_id] for match_id, _, _ in matcher(doc)})
