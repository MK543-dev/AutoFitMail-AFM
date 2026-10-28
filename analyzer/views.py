from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from applications.models import Application

from .forms import NewAnalysisForm
from .models import Analysis, JobDescription, Resume
from .services import jd_utils, roadmap, scorer
from .services.parser import ParseError, extract_text


@login_required
def dashboard(request):
    apps = Application.objects.filter(user=request.user).select_related(
        'jd', 'generated_resume__analysis')
    stats = {
        'total': apps.count(),
        'sent': apps.exclude(sent_at=None).count(),
        'interviews': apps.filter(status='INTERVIEW').count(),
        'avg_score': round(request.user.analyses.aggregate(a=Avg('score'))['a'] or 0),
    }
    return render(request, 'analyzer/dashboard.html', {'stats': stats, 'recent': apps[:5]})


@login_required
def new_analysis(request):
    form = NewAnalysisForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        upload = cd['new_resume']
        try:
            text = extract_text(upload, upload.name)
        except ParseError as exc:
            form.add_error('new_resume', str(exc))
        else:
            upload.seek(0)
            resume = Resume.objects.create(
                user=request.user, title=upload.name, file=upload, text=text)
            parsed = jd_utils.parse_jd(cd['jd_text'])
            jd = JobDescription.objects.create(
                user=request.user,
                title=parsed['title'] or 'Untitled role',
                company=parsed['company'] or 'Unknown company',
                text=cd['jd_text'],
                apply_email=parsed['apply_email'],
                apply_email_cc=', '.join(parsed['cc_emails']),
            )
            r = scorer.score(resume.text, jd.text)
            analysis = Analysis.objects.create(
                user=request.user, resume=resume, jd=jd, score=r['score'],
                required_skills=r['required'], matched_skills=r['matched'],
                missing_skills=r['missing'], optional_missing=r['optional_missing'],
            )
            return redirect('analysis_detail', pk=analysis.pk)
    return render(request, 'analyzer/new.html', {'form': form, 'step': 1})


@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk, user=request.user)
    ctx = {
        'analysis': analysis, 'step': 2,
        'path': roadmap.build(analysis.missing_skills),
        'optional': roadmap.build(analysis.optional_missing),
    }
    return render(request, 'analyzer/analysis.html', ctx)


@login_required
def resumes(request):
    return render(request, 'analyzer/resumes.html',
                  {'resumes': Resume.objects.filter(user=request.user)})


@login_required
def resume_file(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    return FileResponse(resume.file.open('rb'), as_attachment=False, filename=resume.title)


@login_required
@require_POST
def resume_delete(request, pk):
    get_object_or_404(Resume, pk=pk, user=request.user).delete()
    messages.success(request, 'Resume deleted.')
    return redirect('resumes')
