from django import forms
from django.forms import ModelForm
from django.utils.html import strip_tags
from .models import Review

class ReviewForm(ModelForm):
    class Meta:
        model = Review
        # product dan user tidak dimasukkan ke form, karena diisi di view
        # (product dari URL, user dari request.user)
        fields = ["rating", "komentar"]
        labels = {
            "rating": "Rating",
            "komentar": "Komentar",
        }
        widgets = {
            "komentar": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Ceritakan pengalamanmu dengan produk ini...",
            }),
        }
        error_messages = {
            "rating": {
                "required": "Pilih rating 1 sampai 5.",
                "invalid_choice": "Rating harus antara 1 sampai 5.",
            },
            "komentar": {
                "required": "Komentar tidak boleh kosong.",
                "max_length": "Komentar maksimal 1000 karakter.",
            },
        }

    def clean_komentar(self):
        komentar = strip_tags(self.cleaned_data["komentar"]).strip()
        if not komentar:
            raise forms.ValidationError("Komentar tidak boleh kosong.")
        return komentar
