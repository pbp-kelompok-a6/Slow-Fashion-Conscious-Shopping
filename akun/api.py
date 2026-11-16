import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import RegisterForm
from .models import Profile


def _data(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or "{}")
        except ValueError:
            return {}
    return request.POST


@csrf_exempt
@require_POST
def api_login(request):
    d = _data(request)
    user = authenticate(request, username=d.get("username", ""), password=d.get("password", ""))
    if user is None:
        return JsonResponse({"status": False, "message": "Username atau password salah."}, status=401)
    login(request, user)
    profile = Profile.for_user(user)
    return JsonResponse({
        "status": True,
        "message": "Login berhasil.",
        "username": user.username,
        "is_seller": profile.is_seller,
    })


@csrf_exempt
@require_POST
def api_register(request):
    form = RegisterForm(_data(request))
    if not form.is_valid():
        return JsonResponse({
            "status": False,
            "message": "Registrasi gagal.",
            "errors": form.errors.get_json_data(),
        }, status=400)
    user = form.save()
    login(request, user)
    return JsonResponse({"status": True, "message": "Akun berhasil dibuat.", "username": user.username})


@csrf_exempt
@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({"status": True, "message": "Logout berhasil."})