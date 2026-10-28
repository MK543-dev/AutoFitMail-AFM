import os
import uuid

from django.conf import settings
from django.db import models

from analyzer.models import JobDescription
from resume_gen.models import GeneratedResume


def application_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'applications/{instance.user_id}/{uuid.uuid4().hex}{ext}'


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        INTERVIEW = 'INTERVIEW', 'Interview'
        REJECTED = 'REJECTED', 'Rejected'
        OFFER = 'OFFER', 'Offer'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    jd = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='applications')
    generated_resume = models.ForeignKey(GeneratedResume, on_delete=models.SET_NULL, null=True)
    # The user's own resume file, uploaded at the review step. When set, it is
    # attached to the email instead of the generated PDF.
    uploaded_resume = models.FileField(upload_to=application_upload_path, blank=True)
    uploaded_resume_name = models.CharField(max_length=255, blank=True)
    to_email = models.EmailField()
    cc = models.TextField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.jd.title} @ {self.jd.company} ({self.status})'
