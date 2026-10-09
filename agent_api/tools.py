from datetime import date
from django.db.models import Sum, F
from shop.models import Product, Sale, Customer


def get_stock(product_name: str) -> dict:
    """ఒక ఉత్పత్తి నిల్వ ఎంత ఉందో చెబుతుంది (తెలుగు లేదా ఇంగ్లీష్ పేరుతో)."""
    p = (
        Product.objects.filter(telugu_name__icontains=product_name).first()
        or Product.objects.filter(name__icontains=product_name).first()
    )
    if not p:
        return {"found": False, "message": f"'{product_name}' దొరకలేదు"}
    return {
        "found": True,
        "product": p.telugu_name,
        "stock": p.stock,
        "unit": p.unit,
        "is_low": p.stock < p.low_stock_limit,
    }


def low_stock_items() -> list:
    """నిల్వ తక్కువగా ఉన్న ఉత్పత్తుల జాబితా."""
    items = Product.objects.filter(stock__lt=F("low_stock_limit"))
    return [
        {
            "product": p.telugu_name,
            "stock": p.stock,
            "unit": p.unit,
            "limit": p.low_stock_limit,
            "supplier": p.supplier.name if p.supplier else None,
        }
        for p in items
    ]


def today_sales() -> dict:
    """ఈ రోజు మొత్తం అమ్మకాలు."""
    total = (
        Sale.objects.filter(date=date.today()).aggregate(t=Sum("total_amount"))["t"]
        or 0
    )
    count = Sale.objects.filter(date=date.today()).count()
    return {"date": str(date.today()), "total_amount": total, "number_of_sales": count}


def pending_credit() -> list:
    """బాకీ ఉన్న కస్టమర్ల జాబితా (udhar)."""
    customers = Customer.objects.filter(balance_due__gt=0).order_by("-balance_due")
    return [{"name": c.name, "balance_due": c.balance_due} for c in customers]