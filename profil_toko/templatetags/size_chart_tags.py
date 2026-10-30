import requests
from django import template
from django.core.cache import cache

from profil_toko.models import SizeChart, size_sort_key

register = template.Library()

MOCK_API_URL = "https://adbff5e9-8baf-4330-8890-d931a43d0a06.mock.pstmn.io/sizechart"


@register.simple_tag
def size_chart_for(brand):
    if not brand:
        return {"rows": [], "source": None}
    rows = cache.get("mock_sizechart")
    source = "mock API"
    if rows is None:
        try:
            response = requests.get(MOCK_API_URL, timeout=5)
            response.raise_for_status()
            rows = response.json()
            cache.set("mock_sizechart", rows, 300)
        except (requests.RequestException, ValueError):
            rows = [c.to_dict() for c in SizeChart.objects.filter(brand__iexact=brand)]
            source = "database"
    rows = [r for r in rows if str(r.get("brand", "")).lower() == brand.lower()]
    rows.sort(key=lambda r: size_sort_key(str(r.get("size", ""))))
    return {"rows": rows, "source": source}