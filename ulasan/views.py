from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

from listing.models import Product
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
