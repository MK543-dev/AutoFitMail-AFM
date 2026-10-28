import os

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from analyzer.models import Analysis
from resume_gen.models import GeneratedResume

from .models import Application
from .services import draft, mailer


class ReviewForm(forms.Form):
    to_email = forms.EmailField(label='To')
    cc = forms.CharField(required=False, label='Cc (optional)')
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
    reviewed = forms.BooleanField(label='I reviewed the email and the resume PDF')
    send_anyway = forms.BooleanField(
        required=False, label='Send even though I already applied here')
    uploaded_resume = forms.FileField(
        required=False, label='Upload your own resume',
        help_text='PDF or DOCX, max 5 MB. If set, it is sent instead of the generated PDF.')
    remove_uploaded = forms.BooleanField(
        required=False, label='Remove the uploaded resume (send the generated PDF instead)')

    def clean_uploaded_resume(self):
        f = self.cleaned_data.get('uploaded_resume')
        if f:
            if os.path.splitext(f.name)[1].lower() not in ('.pdf', '.docx'):
                raise forms.ValidationError('Only PDF or DOCX files are allowed.')
            if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f'File is larger than {settings.MAX_UPLOAD_MB} MB.')
        return f


def _delete_file(field_file):
    try:
        field_file.delete(save=False)
    except OSError:
        # Windows can refuse to delete a file another process still holds open.
        pass


def _draft_application(request, gen):
    app = Application.objects.filter(user=request.user, generated_resume=gen, status='DRAFT').first()
    if not app:
        subject, body = draft.build_email(request.user, gen.analysis.jd, gen.content)
        app = Application.objects.create(
            user=request.user, jd=gen.analysis.jd, generated_resume=gen,
            to_email=gen.analysis.jd.apply_email, cc=gen.analysis.jd.apply_email_cc,
            subject=subject, body=body,
        )
    return app


@login_required
def prepare(request, resume_id):
    gen = get_object_or_404(GeneratedResume, pk=resume_id, analysis__user=request.user)
    return redirect('review_application', pk=_draft_application(request, gen).pk)


@login_required
@require_POST
def prepare_custom(request, analysis_id):
    """Apply with the user's own resume: no tailored generation required."""
    analysis = get_object_or_404(Analysis, pk=analysis_id, user=request.user)
    gen = GeneratedResume.objects.filter(analysis=analysis, content={}).first()
    if not gen:
        gen = GeneratedResume.objects.create(analysis=analysis, content={})
    return redirect('review_application', pk=_draft_application(request, gen).pk)


@login_required
def review(request, pk):
    app = get_object_or_404(Application, pk=pk, user=request.user)
    if app.status not in ('DRAFT', 'FAILED'):
        return redirect('application_detail', pk=app.pk)
    initial = {'to_email': app.to_email, 'cc': app.cc, 'subject': app.subject, 'body': app.body}
    form = ReviewForm(request.POST or None, request.FILES or None, initial=initial)
    duplicate = Application.objects.filter(
        user=request.user, jd=app.jd, sent_at__isnull=False).exclude(pk=app.pk).exists()
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        if duplicate and not cd['send_anyway']:
            form.add_error('send_anyway', 'You already sent an application for this job. Tick this box to send again.')
        else:
            app.to_email, app.subject, app.body = cd['to_email'], cd['subject'], cd['body']
            app.cc = cd['cc']
            upload = cd.get('uploaded_resume')
            if upload:
                if app.uploaded_resume:
                    _delete_file(app.uploaded_resume)
                app.uploaded_resume = upload
                app.uploaded_resume_name = upload.name[:255]
            elif cd.get('remove_uploaded'):
                if app.uploaded_resume:
                    _delete_file(app.uploaded_resume)
                app.uploaded_resume = ''
                app.uploaded_resume_name = ''
            app.save()
            try:
                ok = mailer.send(app)
            except (mailer.SendLimitError, ValidationError) as exc:
                messages.error(request, str(exc))
            else:
                if ok:
                    messages.success(request, f'Application sent to {app.to_email}.')
                    return redirect('application_detail', pk=app.pk)
                messages.error(request, 'Sending failed. Check the details and try again.')
    ctx = {'app': app, 'form': form, 'duplicate': duplicate, 'step': 4}
    return render(request, 'applications/review.html', ctx)


@login_required
def tracker(request):
    qs = Application.objects.filter(user=request.user).select_related(
        'jd', 'generated_resume__analysis')
    status, q = request.GET.get('status', ''), request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(jd__title__icontains=q) | Q(jd__company__icontains=q))
    return render(request, 'applications/tracker.html',
                  {'apps': qs, 'statuses': Application.Status.choices, 'status': status, 'q': q})


@login_required
def application_detail(request, pk):
    app = get_object_or_404(Application, pk=pk, user=request.user)
    return render(request, 'applications/detail.html', {'app': app, 'step': 5})


@login_required
@require_POST
def update_status(request, pk):
    app = get_object_or_404(Application, pk=pk, user=request.user)
    new = request.POST.get('status')
    # The 'next' parameter was dropped on purpose: it made an open redirect
    # possible (see the doc's section 9 hardening list).
    if new in ('SENT', 'INTERVIEW', 'REJECTED', 'OFFER') and app.sent_at:
        app.status = new
        app.save(update_fields=['status'])
    return redirect('tracker')


@login_required
@require_POST
def delete_application(request, pk):
    get_object_or_404(Application, pk=pk, user=request.user).delete()
    messages.success(request, 'Application deleted.')
    return redirect('tracker')
