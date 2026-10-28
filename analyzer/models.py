import os
import uuid

from django.conf import settings
from django.db import models


def resume_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'resumes/{instance.user_id}/{uuid.uuid4().hex}{ext}'


class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=120)
    file = models.FileField(upload_to=resume_path)
    text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        self.file.delete(save=False)
        super().delete(*args, **kwargs)


class JobDescription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jds')
    title = models.CharField(max_length=160)
    company = models.CharField(max_length=160)
    text = models.TextField()
    apply_email = models.EmailField(blank=True)
    apply_email_cc = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} @ {self.company}'


class Analysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='analyses')
    jd = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='analyses')
    score = models.FloatField(default=0)
    required_skills = models.JSONField(default=list)
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    optional_missing = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.jd.title} @ {self.jd.company} ({self.score}%)'
