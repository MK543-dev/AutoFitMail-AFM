from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Application


@receiver(post_delete, sender=Application, dispatch_uid='applications_delete_uploaded_file')
def delete_uploaded_resume(sender, instance, **kwargs):
    """Bulk cascades don't call Model.delete(); make sure uploaded files go too."""
    if instance.uploaded_resume:
        instance.uploaded_resume.delete(save=False)
