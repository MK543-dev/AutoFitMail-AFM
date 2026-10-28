import os

from django import forms
from django.conf import settings


class NewAnalysisForm(forms.Form):
    new_resume = forms.FileField(
        label='Your resume (PDF or DOCX, max 5 MB)',
        help_text='This file is what gets attached to your application email.')
    jd_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 14}),
        label='Job description',
        help_text='Paste the whole job post - emojis and formatting are fine. '
                  'AFM extracts the role, company and recruiter emails (To + CC) automatically.')

    def clean_new_resume(self):
        f = self.cleaned_data.get('new_resume')
        if f:
            if os.path.splitext(f.name)[1].lower() not in ('.pdf', '.docx'):
                raise forms.ValidationError('Only PDF or DOCX files are allowed.')
            if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f'File is larger than {settings.MAX_UPLOAD_MB} MB.')
        return f
