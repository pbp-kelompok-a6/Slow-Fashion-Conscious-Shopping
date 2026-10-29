from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .forms import RegisterForm, ProfileForm
from .models import Profile
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from pesanan.guards import delete_account
from pesanan.validation import DomainError
# validasi, simpan, ambil, delete data 
def landing(request):
    return render(request, "landing.html")

def register(request):
    if request.method == "POST":
        # Mengambil data dari form
        form = RegisterForm(request.POST) 
        if form.is_valid(): 
            user = form.save()
            # field user pada Profile diisi dengan objek User yang baru saja dibuat.
            Profile.objects.create(user=user) 
            auth_login(request, user) 
            return redirect("akun:profil")
    else:
        form = RegisterForm()
    return render(request, "akun/register.html", {"form": form})

def login_view(request):
    target = request.POST.get("next", request.GET.get("next", ""))
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse("landing")
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect(target)
    else:
        form = AuthenticationForm()
    return render(request, "akun/login.html", {"form": form, "next": target})

@login_required
@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("landing")

@login_required
def profil(request):
    # Hanya menampilkan halaman. Simpan bio ada di edit_profil.
    return render(request, "akun/profil.html", {"profile": request.user.profile})

@login_required
@require_POST
def edit_profil(request):
    form = ProfileForm(request.POST)
    if form.is_valid():
        profile = request.user.profile 
        profile.bio = form.cleaned_data["bio"]
        profile.save()
    return redirect("akun:profil")

@login_required
def hapus_akun(request):
    if request.method == "POST":
        try:
            delete_account(request.user.pk)
        except DomainError as exc:
            if "application/json" in request.headers.get("Accept", ""):
                return JsonResponse({"success": False, "code": exc.code, "message": exc.message}, status=exc.status)
            profile, _ = Profile.objects.get_or_create(user=request.user)
            return render(request, "akun/profil.html", {"profile": profile, "deletion_error": exc.message}, status=exc.status)
        return redirect("landing")
    return render(request, "akun/profil.html", {"profile": request.user.profile})

@login_required
# memastikan view itu hanya bisa dijalankan lewat request POST.
@require_POST 
def toggle_seller(request):
    # Kalau pengguna login adalah burhan, Django mencari profil milik burhan
    profile = request.user.profile 
    profile.is_seller = not profile.is_seller
    profile.save()
    return JsonResponse({"is_seller": profile.is_seller})

@login_required
@require_GET
def profil_json(request):
    profile = request.user.profile
    return JsonResponse({
        "success": True,
        "profile": {
            "username": request.user.username,
            "bio": profile.bio,
            "is_seller": profile.is_seller,
            "date_joined": request.user.date_joined.isoformat(),
        },
    })
