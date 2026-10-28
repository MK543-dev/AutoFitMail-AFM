from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import SignUpForm

LOGIN_ATTEMPT_LIMIT = 10
LOGIN_ATTEMPT_WINDOW = 15 * 60  # seconds


class RateLimitedLoginView(auth_views.LoginView):
    """LoginView plus a simple per-IP failed-attempt limiter (doc section 9)."""

    template_name = 'accounts/login.html'

    def post(self, request, *args, **kwargs):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        key = f'login-fail:{ip}'
        fails = cache.get(key, 0)
        if fails >= LOGIN_ATTEMPT_LIMIT:
            return HttpResponse(
                'Too many failed login attempts. Try again in about 15 minutes.',
                status=429)
        response = super().post(request, *args, **kwargs)
        if response.status_code == 302 and request.user.is_authenticated:
            cache.delete(key)  # a successful login resets the counter
        elif response.status_code == 200:
            cache.set(key, fails + 1, LOGIN_ATTEMPT_WINDOW)
        return response


def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('dashboard')
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def delete_account(request):
    if request.method == 'POST':
        if request.user.check_password(request.POST.get('password', '')):
            request.user.delete()  # cascades to resumes, analyses, PDFs, applications
            logout(request)
            messages.success(request, 'Your account and all data were deleted.')
            return redirect('landing')
        messages.error(request, 'Wrong password.')
    return render(request, 'accounts/delete.html')
