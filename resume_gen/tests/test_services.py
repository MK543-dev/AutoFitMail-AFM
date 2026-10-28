import io
from unittest import mock

import pdfplumber

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from analyzer.models import Analysis, JobDescription, Resume
from resume_gen.models import GeneratedResume
from resume_gen.services import pdf
from resume_gen.services.guard import check
from resume_gen.services.stub import stub_rewrite

RESUME = (
    'Jane Doe\n'
    'jane.doe@example.com | +1 555 010 2030\n'
    'Python developer at Acme Corp since 2020.\n'
    'Skills: Python, Django, SQL, Git, PostgreSQL.\n'
    'Built REST APIs and data pipelines used by internal teams.\n'
    'Education: B.Sc. Computer Science, 2020.\n'
)
JD = 'We need Python, Django and Docker. Nice to have: AWS.'


class StubWriterTests(SimpleTestCase):
    def test_stub_rewrite_only_uses_resume_facts(self):
        content = stub_rewrite(RESUME, JD)
        self.assertEqual(content['name'], 'Jane Doe')
        self.assertNotIn('Docker', content['skills'])
        self.assertTrue(check(content, RESUME))


class PdfRenderTests(SimpleTestCase):
    def test_render_pdf_bytes(self):
        content = stub_rewrite(RESUME, JD)
        data = pdf.render_pdf_bytes(content)
        self.assertTrue(data.startswith(b'%PDF'))
        self.assertGreater(len(data), 500)

    def test_pdf_skips_empty_experience_section(self):
        content = {
            'name': 'Fresher Resume',
            'contact': {'email': '', 'phone': '', 'location': '', 'links': []},
            'summary': 'Graduate with hands-on projects.',
            'skills': ['Python'],
            'experience': [],
            'education': [{'degree': 'B.Tech', 'school': 'X College', 'dates': '2025'}],
            'projects': [],
        }
        data = pdf.render_pdf_bytes(content)
        with pdfplumber.open(io.BytesIO(data)) as doc:
            text = '\n'.join((page.extract_text() or '') for page in doc.pages)
        self.assertNotIn('EXPERIENCE', text.upper())
        self.assertIn('EDUCATION', text.upper())

    def test_pdf_renders_certifications(self):
        content = stub_rewrite(RESUME, JD)
        content['certifications'] = ['Duolingo English Test (CEFR B2) - 105/160']
        data = pdf.render_pdf_bytes(content)
        with pdfplumber.open(io.BytesIO(data)) as doc:
            text = '\n'.join((page.extract_text() or '') for page in doc.pages)
        self.assertIn('CERTIFICATIONS', text.upper())
        self.assertIn('105/160', text)


def _stub_passthrough(resume_text, jd_text, matched_skills):
    """Keep the view flow offline and deterministic (no paid API call in tests)."""
    return stub_rewrite(resume_text, jd_text)


class GenerateFlowTests(TestCase):
    def setUp(self):
        # force_login below: no password value is needed (or stored) for tests.
        self.user = User.objects.create_user('g@x.com', 'g@x.com')
        self.resume = Resume.objects.create(user=self.user, title='cv.txt', text=RESUME, file='resumes/3/x.txt')
        self.jd = JobDescription.objects.create(
            user=self.user, title='Django Developer', company='Acme', text=JD,
            apply_email='hr@acme.com')
        self.analysis = Analysis.objects.create(
            user=self.user, resume=self.resume, jd=self.jd, score=66.7,
            matched_skills=['Python', 'Django'])
        self.client.force_login(self.user)

    def test_generate_creates_pdf_and_edit_saves(self):
        with mock.patch('resume_gen.views.writer.rewrite', side_effect=_stub_passthrough):
            resp = self.client.post(reverse('generate_resume', args=[self.analysis.pk]))
        self.assertEqual(resp.status_code, 302)
        gen = GeneratedResume.objects.get()
        self.assertTrue(gen.pdf_file)

        resp = self.client.get(reverse('resume_pdf', args=[gen.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        b''.join(resp.streaming_content)  # drain and release the file handle
        resp.close()

        resp = self.client.get(reverse('resume_edit', args=[gen.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Jane Doe')

        resp = self.client.post(reverse('resume_edit', args=[gen.pk]), {
            'name': 'Jane Q Doe',
            'summary': 'Python developer who builds REST APIs.',
            'skills': 'Python, Django',
            'exp_0': 'Built REST APIs at Acme Corp.\nMentored two junior developers.',
        })
        self.assertEqual(resp.status_code, 302)
        gen.refresh_from_db()
        self.assertEqual(gen.content['name'], 'Jane Q Doe')
        self.assertEqual(gen.content['skills'], ['Python', 'Django'])
        self.assertIn('Mentored two junior developers.', gen.content['experience'][0]['bullets'])

    def test_other_user_cannot_open_generated_resume(self):
        other = User.objects.create_user('h@x.com', 'h@x.com')
        gen = GeneratedResume.objects.create(analysis=self.analysis, content={})
        self.client.force_login(other)
        resp = self.client.get(reverse('resume_edit', args=[gen.pk]))
        self.assertEqual(resp.status_code, 404)
