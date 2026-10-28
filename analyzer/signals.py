from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Resume


@receiver(post_delete, sender=Resume, dispatch_uid='analyzer_resume_delete_file')
def delete_resume_file(sender, instance, **kwargs):
    """Bulk cascades don't call Model.delete(); make sure files go too."""
    if instance.file:
        instance.file.delete(save=False)
