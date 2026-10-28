from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'jd', 'to_email', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)
