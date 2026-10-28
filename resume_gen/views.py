from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from analyzer.models import Analysis

from .models import GeneratedResume
from .services import pdf, writer
from .services.guard import GuardError


def _apply_post(content, post):
    content['name'] = post.get('name', '').strip()
    content['summary'] = post.get('summary', '').strip()
    content['skills'] = [s.strip() for s in post.get('skills', '').split(',') if s.strip()]
    for i, job in enumerate(content.get('experience', [])):
        job['bullets'] = [ln.strip() for ln in post.get(f'exp_{i}', '').splitlines() if ln.strip()]
    return content


@login_required
@require_POST
def generate(request, analysis_id):
    analysis = get_object_or_404(Analysis, pk=analysis_id, user=request.user)
    try:
        content = writer.rewrite(analysis.resume.text, analysis.jd.text, analysis.matched_skills)
    except GuardError as exc:
        messages.error(
            request,
            f'The draft was rejected because it added details not in your resume ({exc}). Try again.')
        return redirect('analysis_detail', pk=analysis.pk)
    except writer.WriterError as exc:
        # Show the real reason (401/403/404/429/connection) instead of a
        # generic message - see check_llm.py for a direct test.
        messages.error(request, f'The writing service returned an error: {exc}')
        return redirect('analysis_detail', pk=analysis.pk)
    gen = GeneratedResume.objects.create(analysis=analysis, content=content)
    pdf.save_pdf(gen)
    return redirect('resume_edit', pk=gen.pk)


@login_required
def resume_edit(request, pk):
    gen = get_object_or_404(GeneratedResume, pk=pk, analysis__user=request.user)
    if request.method == 'POST':
        gen.content = _apply_post(gen.content, request.POST)
        gen.save()
        pdf.save_pdf(gen)
        messages.success(request, 'Resume updated.')
        return redirect('resume_edit', pk=gen.pk)
    return render(request, 'resume_gen/edit.html', {'gen': gen, 'step': 3})


@login_required
def resume_pdf(request, pk):
    gen = get_object_or_404(GeneratedResume, pk=pk, analysis__user=request.user)
    if not gen.pdf_file:
        messages.info(request, 'No PDF has been generated for this draft yet.')
        return redirect('resume_edit', pk=gen.pk)
    return FileResponse(gen.pdf_file.open('rb'), content_type='application/pdf')
