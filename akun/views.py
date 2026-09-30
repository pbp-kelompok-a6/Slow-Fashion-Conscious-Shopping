from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import RegisterForm, ProfileForm
from .models import Profile

def landing(request):
    return render(request, "landing.html")

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            auth_login(request, user)
            return redirect("akun:profil")
    else:
        form = RegisterForm()
    return render(request, "akun/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("landing")
    else:
        form = AuthenticationForm()
    return render(request, "akun/login.html", {"form": form})

@login_required
def logout_view(request):
    auth_logout(request)
    return redirect("landing")

@login_required
def profil(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile.bio = form.cleaned_data["bio"]
            profile.save()
    return render(request, "akun/profil.html", {"profile": profile})

@login_required
def hapus_akun(request):
    if request.method == "POST":
        request.user.delete()
        return redirect("landing")
    return render(request, "akun/profil.html", {"profile": request.user.profile})

@login_required
@require_POST
def toggle_seller(request):
    profile = request.user.profile
    profile.is_seller = not profile.is_seller
    profile.save()
    return JsonResponse({"is_seller": profile.is_seller})