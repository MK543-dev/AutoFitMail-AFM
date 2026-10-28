import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from analyzer.models import Analysis, JobDescription, Resume
from applications.models import Application
from applications.services import mailer
from resume_gen.models import GeneratedResume
from resume_gen.services.writer import WriterError


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MailerTests(TestCase):
    def setUp(self):
        # force_login only: no password values in tests.
        self.user = User.objects.create_user('a@x.com', 'a@x.com')
        resume = Resume.objects.create(user=self.user, title='r.pdf', text='x' * 120, file='resumes/r.pdf')
        jd = JobDescription.objects.create(user=self.user, title='Dev', company='Acme', text='Python')
        analysis = Analysis.objects.create(user=self.user, resume=resume, jd=jd)
        self.gen = GeneratedResume.objects.create(analysis=analysis, content={})
        self.gen.pdf_file.save('t.pdf', ContentFile(b'%PDF-1.4 test'))
        self.app = Application.objects.create(
            user=self.user, jd=jd, generated_resume=self.gen,
            to_email='hr@acme.com', subject='Hi', body='Body')
        self.client.force_login(self.user)

    def test_send_success_marks_sent_and_attaches_pdf(self):
        self.assertTrue(mailer.send(self.app))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')
        self.assertEqual(mail.outbox[0].reply_to, ['a@x.com'])
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'SENT')
        self.assertIsNotNone(self.app.sent_at)

    def test_daily_limit(self):
        with self.settings(DAILY_SEND_LIMIT=0):
            with self.assertRaises(mailer.SendLimitError):
                mailer.send(self.app)

    def test_other_user_cannot_open_application(self):
        other = User.objects.create_user('b@x.com', 'b@x.com')
        self.client.force_login(other)
        r = self.client.get(reverse('application_detail', args=[self.app.pk]))
        self.assertEqual(r.status_code, 404)

    def test_review_requires_confirmation_checkbox(self):
        r = self.client.post(reverse('review_application', args=[self.app.pk]),
                             {'to_email': 'hr@acme.com', 'subject': 'Hi', 'body': 'Body'})
        self.assertEqual(r.status_code, 200)  # form re-rendered with an error
        self.assertEqual(len(mail.outbox), 0)  # nothing sent without the reviewed box

    def test_review_sends_and_marks_sent(self):
        r = self.client.post(reverse('review_application', args=[self.app.pk]),
                             {'to_email': 'hr@acme.com', 'subject': 'App', 'body': 'Hello',
                              'reviewed': 'on'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'SENT')

    def test_duplicate_send_needs_explicit_override(self):
        self.app.status = 'SENT'
        self.app.sent_at = timezone.now()
        self.app.save()
        app2 = Application.objects.create(
            user=self.user, jd=self.app.jd, generated_resume=self.gen,
            to_email='hr@acme.com', subject='Hi again', body='Body')
        payload = {'to_email': 'hr@acme.com', 'subject': 'Hi again', 'body': 'Body', 'reviewed': 'on'}
        r = self.client.post(reverse('review_application', args=[app2.pk]), payload)
        self.assertEqual(r.status_code, 200)   # duplicate warning blocks the send
        self.assertEqual(len(mail.outbox), 0)
        payload['send_anyway'] = 'on'
        r = self.client.post(reverse('review_application', args=[app2.pk]), payload)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_prepare_builds_draft_email(self):
        self.app.delete()
        with mock.patch('applications.services.draft.generate_text', side_effect=WriterError('offline')):
            r = self.client.get(reverse('prepare_application', args=[self.gen.pk]))
        self.assertEqual(r.status_code, 302)
        app = Application.objects.get()
        self.assertEqual(app.status, 'DRAFT')
        self.assertIn('Dev', app.subject)
        self.assertIn('Acme', app.body)

    def test_ai_generated_email_is_used(self):
        self.app.delete()
        self.gen.content = {
            'name': 'A User', 'summary': 'Dev', 'skills': ['Python'],
            'experience': [], 'education': [], 'projects': [],
        }
        self.gen.save()
        fake = '{"subject": "AI Subject", "body": "AI body text"}'
        with mock.patch('applications.services.draft.generate_text', return_value=fake):
            r = self.client.get(reverse('prepare_application', args=[self.gen.pk]))
        self.assertEqual(r.status_code, 302)
        app = Application.objects.get()
        self.assertEqual(app.subject, 'AI Subject')
        self.assertEqual(app.body, 'AI body text')

    def test_smtp_failure_marks_failed_with_error(self):
        with mock.patch('django.core.mail.EmailMessage.send', side_effect=Exception('SMTP down')):
            self.assertFalse(mailer.send(self.app))
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'FAILED')
        self.assertIn('SMTP down', self.app.error)

    def test_uploaded_resume_replaces_generated_pdf(self):
        upload = SimpleUploadedFile('My_Own_Resume.pdf', b'%PDF-1.4 custom resume', content_type='application/pdf')
        r = self.client.post(reverse('review_application', args=[self.app.pk]), {
            'to_email': 'hr@acme.com', 'subject': 'App', 'body': 'Hello', 'reviewed': 'on',
            'uploaded_resume': upload,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0], 'My_Own_Resume.pdf')
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')
        self.app.refresh_from_db()
        self.assertEqual(self.app.uploaded_resume_name, 'My_Own_Resume.pdf')
        self.assertTrue(self.app.uploaded_resume)

    def test_upload_rejects_bad_extension(self):
        upload = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        r = self.client.post(reverse('review_application', args=[self.app.pk]), {
            'to_email': 'hr@acme.com', 'subject': 'App', 'body': 'Hello', 'reviewed': 'on',
            'uploaded_resume': upload,
        })
        self.assertEqual(r.status_code, 200)  # form re-rendered with an error
        self.assertEqual(len(mail.outbox), 0)

    def test_mailer_prefers_uploaded_file(self):
        self.app.uploaded_resume.save('own.pdf', ContentFile(b'%PDF-1.4 own'), save=True)
        self.app.uploaded_resume_name = 'own.pdf'
        self.app.save()
        self.assertTrue(mailer.send(self.app))
        self.assertEqual(mail.outbox[0].attachments[0][0], 'own.pdf')

    def test_remove_upload_falls_back_to_generated_pdf(self):
        self.app.uploaded_resume.save('own.pdf', ContentFile(b'%PDF-1.4 own'), save=True)
        self.app.uploaded_resume_name = 'own.pdf'
        self.app.save()
        r = self.client.post(reverse('review_application', args=[self.app.pk]), {
            'to_email': 'hr@acme.com', 'subject': 'App', 'body': 'Hello', 'reviewed': 'on',
            'remove_uploaded': 'on',
        })
        self.assertEqual(r.status_code, 302)
        self.app.refresh_from_db()
        self.assertFalse(bool(self.app.uploaded_resume))
        self.assertEqual(mail.outbox[0].attachments[0][0], 'Resume_Acme.pdf')

    def test_send_without_any_attachment_fails(self):
        gen2 = GeneratedResume.objects.create(analysis=self.gen.analysis, content={})
        app2 = Application.objects.create(
            user=self.user, jd=self.app.jd, generated_resume=gen2,
            to_email='hr@acme.com', subject='Hi', body='Body')
        self.assertFalse(mailer.send(app2))
        app2.refresh_from_db()
        self.assertEqual(app2.status, 'FAILED')
        self.assertIn('resume', app2.error.lower())

    def test_apply_with_own_resume_without_generating(self):
        analysis_pk = self.gen.analysis_id
        self.app.delete()
        self.gen.delete()
        r = self.client.post(reverse('prepare_custom', args=[analysis_pk]))
        self.assertEqual(r.status_code, 302)
        app = Application.objects.get()
        self.assertEqual(app.status, 'DRAFT')
        r = self.client.get(reverse('review_application', args=[app.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No resume attached yet')

    def test_cc_is_passed_to_the_email(self):
        self.app.cc = 'boss@acme.com'
        self.app.save()
        self.assertTrue(mailer.send(self.app))
        self.assertEqual(mail.outbox[0].cc, ['boss@acme.com'])
