from django.contrib import admin

from .models import GeneratedResume


@admin.register(GeneratedResume)
class GeneratedResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'created_at')
