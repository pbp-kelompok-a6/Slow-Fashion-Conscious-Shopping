from django.urls import path
from . import views
from . import views, api
app_name = "akun"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profil/", views.profil, name="profil"),
    path("profil/edit/", views.edit_profil, name="edit_profil"),
    path("hapus/", views.hapus_akun, name="hapus_akun"),
    path("toggle-seller/", views.toggle_seller, name="toggle_seller"),
    path("json/", views.profil_json, name="profil_json"),
    path("api/login/", api.api_login, name="api_login"),
    path("api/register/", api.api_register, name="api_register"),
    path("api/logout/", api.api_logout, name="api_logout"),
    path("api/profil/", api.api_profil, name="api_profil"),
    path("api/profil/edit/", api.api_edit_profil, name="api_edit_profil"),
    path("api/toggle-seller/", api.api_toggle_seller, name="api_toggle_seller"),
    path("api/hapus/", api.api_hapus_akun, name="api_hapus_akun"),
]