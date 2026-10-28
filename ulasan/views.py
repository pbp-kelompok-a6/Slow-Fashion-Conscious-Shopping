from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from listing.models import Product
from .forms import ReviewForm
from .models import Review

def product_reviews(request, product_id):
    # Halaman daftar ulasan satu produk. Isi daftarnya dimuat lewat AJAX dari show_json.
    product = get_object_or_404(Product, pk=product_id)
    return render(request, "ulasan/product_reviews.html", {"product": product})

def show_json(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    reviews = Review.objects.filter(product=product)

    # Filter data: urutkan berdasarkan terbaru (default) atau rating tertinggi
    sort = request.GET.get("sort", "terbaru")
    if sort == "rating":
        reviews = reviews.order_by("-rating", "-created_at")
    else:
        sort = "terbaru"
        reviews = reviews.order_by("-created_at")

    # Data dirakit manual (bukan serializers.serialize) supaya bisa menambahkan
    # username penulis dan is_owner untuk pengguna yang sedang login
    data = []
    for review in reviews:
        data.append({
            "id": str(review.id),
            "username": review.user.username,
            "rating": review.rating,
            "komentar": review.komentar,
            "created_at": review.created_at.strftime("%d %b %Y"),
            "is_edited": (review.updated_at - review.created_at).total_seconds() > 1,
            "is_owner": request.user.is_authenticated and review.user_id == request.user.id,
        })

    jumlah = len(data)
    rata_rata = round(sum(r["rating"] for r in data) / jumlah, 1) if jumlah > 0 else 0

    return JsonResponse({
        "product_id": product.pk,
        "sort": sort,
        "jumlah": jumlah,
        "rata_rata": rata_rata,
        "reviews": data,
    })

# Tidak memakai @login_required: untuk request AJAX, login_required akan redirect
# ke halaman login (HTML, status 200) sehingga fetch tidak tahu kalau gagal.
# Jadi pengecekan login dilakukan manual dan dibalas JSON 403 (Tutorial 5).
@require_POST
def create_review(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Kamu harus login untuk menulis ulasan."}, status=403)

    product = get_object_or_404(Product, pk=product_id)

    if product.seller_id == request.user.id:
        return JsonResponse({"message": "Kamu tidak bisa mengulas produkmu sendiri."}, status=403)

    if Review.objects.filter(product=product, user=request.user).exists():
        return JsonResponse({"message": "Kamu sudah mengulas produk ini."}, status=400)

    form = ReviewForm(request.POST)
    if form.is_valid():
        # commit=False: objek dibuat tapi belum disimpan, karena product dan user
        # tidak ada di form dan harus diisi dulu dari view
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        return JsonResponse({"message": "Ulasan berhasil dikirim. Terima kasih!"}, status=201)

    return JsonResponse({
        "message": "Ulasan gagal dikirim. Periksa kembali isian kamu.",
        "errors": form.errors.get_json_data(),
    }, status=400)
