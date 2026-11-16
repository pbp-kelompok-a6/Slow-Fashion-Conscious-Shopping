import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import ProfileForm, RegisterForm
from .models import Profile
from .views import user_has_store

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
def _auth_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"status": False, "message": "Belum login."}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _profile_payload(user):
    profile = Profile.for_user(user)
    return {
        "username": user.username,
        "bio": profile.bio,
        "is_seller": profile.is_seller,
        "has_store": user_has_store(user),
        "date_joined": user.date_joined.isoformat(),
        "product_count": user.product_listings.count(),
    }


@require_GET
@_auth_required
def api_profil(request):
    return JsonResponse({"status": True, "profile": _profile_payload(request.user)})


@csrf_exempt
@require_POST
@_auth_required
def api_edit_profil(request):
    profile = Profile.for_user(request.user)
    form = ProfileForm(_data(request), instance=profile)
    if not form.is_valid():
        return JsonResponse({
            "status": False,
            "message": "Bio gagal disimpan.",
            "errors": form.errors.get_json_data(),
        }, status=400)
    form.save()
    return JsonResponse({
        "status": True,
        "message": "Bio berhasil disimpan.",
        "profile": _profile_payload(request.user),
    })


@csrf_exempt
@require_POST
@_auth_required
def api_toggle_seller(request):
    profile = Profile.for_user(request.user)
    profile.is_seller = not profile.is_seller
    profile.save(update_fields=["is_seller"])
    if profile.is_seller:
        message = "Mode seller aktif."
        if not user_has_store(request.user):
            message = "Mode seller aktif. Lengkapi profil tokomu dulu, ya."
    else:
        message = "Mode seller dinonaktifkan."
    return JsonResponse({
        "status": True,
        "message": message,
        "profile": _profile_payload(request.user),
    })


@csrf_exempt
@require_POST
@_auth_required
def api_hapus_akun(request):
    user = request.user
    try:
        user.delete()
    except ProtectedError:
        return JsonResponse({
            "status": False,
            "message": "Akun tidak dapat dihapus karena masih memiliki riwayat pesanan.",
        }, status=409)
    logout(request)
    return JsonResponse({"status": True, "message": "Akun kamu sudah dihapus."})