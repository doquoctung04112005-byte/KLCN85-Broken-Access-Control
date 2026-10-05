from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import UserProfile


def _current_profile(user):
    return (
        UserProfile.objects.select_related("department")
        .filter(user=user)
        .first()
    )


@login_required
def dashboard(request):
    return render(
        request,
        "accounts/dashboard.html",
        {"profile": _current_profile(request.user)},
    )


@login_required
def profile(request):
    return render(
        request,
        "accounts/profile.html",
        {"profile": _current_profile(request.user)},
    )
