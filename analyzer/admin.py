from django.contrib import admin

from .models import Analysis, JobDescription, Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'uploaded_at')


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'company', 'user', 'apply_email', 'created_at')


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'score', 'created_at')
