from django.urls import path

from . import views

urlpatterns = [
    path('analysis/<int:analysis_id>/generate/', views.generate, name='generate_resume'),
    path('resume/<int:pk>/', views.resume_edit, name='resume_edit'),
    path('resume/<int:pk>/pdf/', views.resume_pdf, name='resume_pdf'),
]
