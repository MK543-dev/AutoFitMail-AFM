from django.test import SimpleTestCase, override_settings

from resume_gen.services.guard import GuardError, check

RESUME = 'Jane Doe. Python developer at Acme Corp since 2020. Skills: Python, Django.'
GOOD = {
    'name': 'Jane Doe',
    'summary': 'Python developer',
    'skills': ['Python', 'Django'],
    'experience': [{'title': 'Python developer', 'company': 'Acme Corp', 'dates': '2020', 'bullets': []}],
    'education': [],
}


class GuardTests(SimpleTestCase):
    def test_valid_output_passes(self):
        self.assertTrue(check(GOOD, RESUME))

    def test_invented_skill_rejected(self):
        bad = {**GOOD, 'skills': ['Python', 'Kubernetes']}
        with self.assertRaises(GuardError):
            check(bad, RESUME)

    def test_invented_number_rejected(self):
        bad = {**GOOD, 'summary': 'Python developer with 10 years of experience'}
        with self.assertRaises(GuardError):
            check(bad, RESUME)

    def test_invented_company_rejected(self):
        job = {'title': 'Python developer', 'company': 'Globex', 'dates': '2020', 'bullets': []}
        with self.assertRaises(GuardError):
            check({**GOOD, 'experience': [job]}, RESUME)

    def test_missing_keys_rejected(self):
        bad = {k: v for k, v in GOOD.items() if k != 'summary'}
        with self.assertRaises(GuardError):
            check(bad, RESUME)

    def test_alias_backed_skill_passes(self):
        # The resume says "postgres"; the canonical catalog name is "PostgreSQL".
        resume = RESUME + ' Worked with postgres daily.'
        data = {**GOOD, 'skills': ['Python', 'Django', 'PostgreSQL']}
        self.assertTrue(check(data, resume))

    def test_alias_without_resume_support_rejected(self):
        data = {**GOOD, 'skills': ['Python', 'Django', 'PostgreSQL']}
        with self.assertRaises(GuardError):
            check(data, RESUME)

    def test_jd_skill_allowed_when_missing_from_resume(self):
        data = {**GOOD, 'skills': ['Python', 'Django', 'Kubernetes']}
        self.assertTrue(check(data, RESUME, jd_text='We deploy on Kubernetes.'))

    def test_jd_phrase_skill_allowed(self):
        data = {**GOOD, 'skills': ['Python', 'Django', 'Technical Troubleshooting']}
        jd = 'Required: basic computer troubleshooting knowledge.'
        self.assertTrue(check(data, RESUME, jd_text=jd))

    def test_strict_mode_rejects_jd_only_skill(self):
        data = {**GOOD, 'skills': ['Python', 'Django', 'Kubernetes']}
        with override_settings(ALLOW_JD_SKILLS=False):
            with self.assertRaises(GuardError):
                check(data, RESUME, jd_text='We deploy on Kubernetes.')
