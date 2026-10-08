import random
from datetime import date, timedelta
from shop.models import Supplier, Product, Sale, Customer


def run():
    # పాత డేటా తీసేయడం
    Sale.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()
    Supplier.objects.all().delete()

    # Suppliers
    s1 = Supplier.objects.create(name="Sri Lakshmi Traders", phone="9876500001")
    s2 = Supplier.objects.create(name="Venkateswara Wholesale", phone="9876500002")

    # (English, తెలుగు, unit, stock, limit, price, supplier)
    items = [
        ("Rice", "బియ్యం", "kg", 8, 20, 55, s1),
        ("Toor Dal", "కందిపప్పు", "kg", 25, 10, 140, s1),
        ("Sugar", "చక్కెర", "kg", 5, 15, 45, s1),
        ("Salt", "ఉప్పు", "kg", 30, 10, 20, s2),
        ("Oil", "నూనె", "litre", 6, 10, 130, s2),
        ("Tea Powder", "టీ పొడి", "packet", 18, 8, 80, s2),
        ("Wheat Flour", "గోధుమ పిండి", "kg", 12, 15, 40, s1),
        ("Chilli Powder", "కారం", "kg", 9, 5, 220, s2),
        ("Turmeric", "పసుపు", "kg", 4, 3, 160, s2),
        ("Soap", "సబ్బు", "piece", 40, 15, 35, s1),
        ("Biscuits", "బిస్కెట్లు", "packet", 50, 20, 10, s2),
        ("Milk", "పాలు", "litre", 15, 10, 60, s2),
    ]

    products = []
    for en, te, unit, stock, limit, price, sup in items:
        p = Product.objects.create(
            name=en, telugu_name=te, unit=unit,
            stock=stock, low_stock_limit=limit, price=price, supplier=sup,
        )
        products.append(p)

    # గత 7 రోజుల అమ్మకాలు
    for day in range(7):
        d = date.today() - timedelta(days=day)
        for p in random.sample(products, 6):
            qty = random.randint(1, 5)
            Sale.objects.create(
                product=p, quantity=qty, total_amount=qty * p.price, date=d
            )

    # బాకీ ఉన్న కస్టమర్లు
    Customer.objects.create(name="Ramesh", phone="9000000001", balance_due=1200)
    Customer.objects.create(name="Lakshmi", phone="9000000002", balance_due=450)
    Customer.objects.create(name="Suresh", phone="9000000003", balance_due=0)
    Customer.objects.create(name="Padma", phone="9000000004", balance_due=2300)

    print("Demo డేటా సిద్ధం!")