from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import UserProfile

from .forms import DocumentForm
from .models import Document


def _profile_for(user):
    return (
        UserProfile.objects.select_related("department")
        .filter(user=user)
        .first()
    )


def _visible_documents(user, profile):
    if profile is None:
        return Document.objects.none()

    if profile.role == UserProfile.Role.ADMIN:
        return Document.objects.all()

    if profile.role == UserProfile.Role.DEPARTMENT_HEAD:
        if profile.department_id is None:
            return Document.objects.none()
        return Document.objects.filter(department_id=profile.department_id)

    if profile.role == UserProfile.Role.EMPLOYEE:
        return Document.objects.filter(owner=user)

    return Document.objects.none()


def _can_edit(document, user, profile):
    if profile is None:
        return False
    if profile.role == UserProfile.Role.ADMIN:
        return True
    return (
        profile.role in (UserProfile.Role.EMPLOYEE, UserProfile.Role.DEPARTMENT_HEAD)
        and document.owner_id == user.pk
    )


@login_required
@require_GET
def document_list(request):
    profile = _profile_for(request.user)
    documents = _visible_documents(request.user, profile).select_related(
        "owner", "department"
    )
    return render(
        request,
        "documents/list.html",
        {
            "documents": documents,
            "profile": profile,
            "can_create": bool(profile and profile.department_id),
        },
    )


@login_required
@require_GET
def document_detail(request, pk):
    profile = _profile_for(request.user)
    document = get_object_or_404(
        _visible_documents(request.user, profile).select_related("owner", "department"),
        pk=pk,
    )
    return render(
        request,
        "documents/detail.html",
        {"document": document, "can_edit": _can_edit(document, request.user, profile)},
    )


@login_required
@require_http_methods(["GET", "POST"])
def document_create(request):
    profile = _profile_for(request.user)
    if profile is None:
        return render(
            request,
            "documents/access_denied.html",
            {"message": "Tài khoản chưa có hồ sơ. Quản trị viên cần bổ sung hồ sơ trước khi tạo tài liệu."},
            status=403,
        )
    if profile.department_id is None:
        return render(
            request,
            "documents/access_denied.html",
            {"message": "Hồ sơ chưa có phòng ban. Quản trị viên cần gán phòng ban trước khi tạo tài liệu."},
            status=403,
        )

    form = DocumentForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.owner = request.user
        document.department = profile.department
        document.save()
        return redirect("document_detail", pk=document.pk)

    return render(request, "documents/form.html", {"form": form, "is_edit": False})


@login_required
@require_http_methods(["GET", "POST"])
def document_edit(request, pk):
    profile = _profile_for(request.user)
    document = get_object_or_404(
        _visible_documents(request.user, profile),
        pk=pk,
    )
    if not _can_edit(document, request.user, profile):
        return render(
            request,
            "documents/access_denied.html",
            {"message": "Bạn không có quyền sửa tài liệu này."},
            status=403,
        )

    form = DocumentForm(request.POST if request.method == "POST" else None, instance=document)
    if request.method == "POST" and form.is_valid():
        updated_document = form.save(commit=False)
        updated_document.save(update_fields=["title", "content", "updated_at"])
        return redirect("document_detail", pk=document.pk)

    return render(
        request,
        "documents/form.html",
        {"form": form, "document": document, "is_edit": True},
    )
