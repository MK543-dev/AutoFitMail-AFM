from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('accounts/', include('accounts.urls')),
    path('', include('analyzer.urls')),
    path('', include('resume_gen.urls')),
    path('', include('applications.urls')),
]

# Uploaded files and generated PDFs are never served through MEDIA_URL.
# They are streamed only by login_required views using FileResponse,
# so one user can never open another user's file.
