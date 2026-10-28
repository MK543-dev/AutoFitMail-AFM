from django.db import models

from analyzer.models import Analysis


class GeneratedResume(models.Model):
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name='generated')
    content = models.JSONField(default=dict)  # name, contact, summary, skills, experience, education, projects
    pdf_file = models.FileField(upload_to='generated/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def delete(self, *args, **kwargs):
        self.pdf_file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'Generated resume #{self.pk} for {self.analysis.jd.title}'
