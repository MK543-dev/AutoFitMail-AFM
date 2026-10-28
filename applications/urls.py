from django.urls import path

from . import views

urlpatterns = [
    path('apply/<int:resume_id>/', views.prepare, name='prepare_application'),
    path('analysis/<int:analysis_id>/apply-custom/', views.prepare_custom, name='prepare_custom'),
    path('applications/', views.tracker, name='tracker'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/review/', views.review, name='review_application'),
    path('applications/<int:pk>/status/', views.update_status, name='update_status'),
    path('applications/<int:pk>/delete/', views.delete_application, name='delete_application'),
]
