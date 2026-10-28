from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import GeneratedResume


@receiver(post_delete, sender=GeneratedResume, dispatch_uid='resume_gen_pdf_delete_file')
def delete_generated_pdf(sender, instance, **kwargs):
    """Bulk cascades don't call Model.delete(); make sure PDFs go too."""
    if instance.pdf_file:
        instance.pdf_file.delete(save=False)
