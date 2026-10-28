from io import BytesIO

from django.core.files.base import ContentFile
from django.template.loader import render_to_string

try:
    from weasyprint import HTML

    HAS_WEASYPRINT = True
except (OSError, ImportError):  # OSError: Pango/GTK runtime missing (common on Windows)
    HAS_WEASYPRINT = False


def render_pdf_bytes(content):
    """Render the resume JSON to PDF bytes.

    Prefers WeasyPrint (best CSS support); falls back to xhtml2pdf when the
    Pango runtime is unavailable so the app still produces a clean PDF.
    """
    html = render_to_string('resume_gen/resume_pdf.html', {'r': content})
    if HAS_WEASYPRINT:
        try:
            return HTML(string=html).write_pdf()
        except Exception:  # noqa: BLE001 - any WeasyPrint failure falls through
            pass
    from xhtml2pdf import pisa

    out = BytesIO()
    result = pisa.CreatePDF(html, dest=out)
    if result.err:
        raise RuntimeError('PDF rendering failed.')
    return out.getvalue()


def save_pdf(generated):
    data = render_pdf_bytes(generated.content)
    try:
        generated.pdf_file.delete(save=False)
    except OSError:
        # Windows can refuse to delete a file another process still holds open;
        # the new file then simply gets a fresh name instead.
        pass
    generated.pdf_file.save(f'resume_{generated.pk}.pdf', ContentFile(data), save=True)
