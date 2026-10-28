import os

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.text import get_valid_filename

from applications.models import Application

DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


class SendLimitError(Exception):
    pass


def sends_today(user):
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return Application.objects.filter(user=user, sent_at__gte=start).count()


def _attachment(app):
    """Return (file, filename, mime) to attach — the user's own upload wins."""
    if app.uploaded_resume and app.uploaded_resume.name:
        name = os.path.basename(app.uploaded_resume_name or app.uploaded_resume.name)
        mime = 'application/pdf' if name.lower().endswith('.pdf') else DOCX_MIME
        return app.uploaded_resume, get_valid_filename(name), mime
    gen = app.generated_resume
    if gen and gen.pdf_file and gen.pdf_file.name:
        filename = get_valid_filename(f'{app.user.get_full_name() or "Resume"}_{app.jd.company}.pdf')
        return gen.pdf_file, filename, 'application/pdf'
    return None, None, None


def _cc_list(app):
    raw = (app.cc or '').replace(';', ',')
    return [e.strip() for e in raw.split(',') if e.strip()]


def send(app):
    """Send the application email with the resume attached. Returns True on success."""
    if sends_today(app.user) >= settings.DAILY_SEND_LIMIT:
        raise SendLimitError('Daily send limit reached. Try again tomorrow.')
    attachment, filename, mime = _attachment(app)
    if attachment is None:
        app.status = Application.Status.FAILED
        app.error = 'No resume attachment. Generate a tailored resume or upload your own.'
        app.save(update_fields=['status', 'error'])
        return False
    validate_email(app.to_email)
    msg = EmailMessage(
        subject=app.subject,
        body=app.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[app.to_email],
        reply_to=[app.user.email],
        cc=_cc_list(app),
    )
    with attachment.open('rb') as fh:
        msg.attach(filename, fh.read(), mime)
    try:
        msg.send(fail_silently=False)
    except Exception as exc:  # SMTP, network, auth errors
        app.status = Application.Status.FAILED
        app.error = str(exc)[:500]
        app.save(update_fields=['status', 'error'])
        return False
    app.status = Application.Status.SENT
    app.sent_at = timezone.now()
    app.error = ''
    app.save(update_fields=['status', 'sent_at', 'error'])
    return True
