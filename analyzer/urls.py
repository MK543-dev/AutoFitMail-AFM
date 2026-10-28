from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('new/', views.new_analysis, name='new_analysis'),
    path('analysis/<int:pk>/', views.analysis_detail, name='analysis_detail'),
    path('resumes/', views.resumes, name='resumes'),
    path('resumes/<int:pk>/file/', views.resume_file, name='resume_file'),
    path('resumes/<int:pk>/delete/', views.resume_delete, name='resume_delete'),
]
