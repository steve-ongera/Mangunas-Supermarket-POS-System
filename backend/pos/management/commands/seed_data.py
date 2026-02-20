"""
Management command: seed_data
Usage:
    python manage.py seed_data
    python manage.py seed_data --images-dir "D:/gadaf/Documents/Mkurugenzi – Merch_files"
    python manage.py seed_data --clear   (wipe existing data first)

Populates:p
  - Categories (10)
  - Products   (60, with images randomly picked from your local folder)
  - Customers  (20)
  - Sample orders (15 completed)
"""

import os
import random
import shutil
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from pos.models import Category, Customer, Order, OrderItem, Payment, Product, StockMovement


# ─── Realistic supermarket data ───────────────────────────────────────────────

CATEGORIES = [
    ("Beverages",       "Soft drinks, juices, water, energy drinks"),
    ("Dairy & Eggs",    "Milk, cheese, yoghurt, butter, eggs"),
    ("Bakery",          "Bread, cakes, biscuits, pastries"),
    ("Grains & Cereals","Rice, maize flour, wheat flour, pasta, oats"),
    ("Cooking Oils",    "Vegetable oil, sunflower oil, ghee"),
    ("Meat & Poultry",  "Fresh chicken, beef, pork, sausages"),
    ("Fruits & Veg",    "Fresh fruits and vegetables"),
    ("Household",       "Detergents, cleaning supplies, toiletries"),
    ("Snacks & Confec", "Crisps, sweets, chocolates, nuts"),
    ("Baby & Kids",     "Baby food, diapers, formula milk"),
]

PRODUCTS = [
    # (name, category_name, price, cost_price, stock, barcode_suffix)
    # Beverages
    ("Coca-Cola 500ml",          "Beverages",       65,  40,  150, "001"),
    ("Pepsi 500ml",              "Beverages",       60,  38,  120, "002"),
    ("Sprite 500ml",             "Beverages",       65,  40,   90, "003"),
    ("Minute Maid Orange 300ml", "Beverages",       55,  32,  200, "004"),
    ("Dasani Water 500ml",       "Beverages",       40,  22,  300, "005"),
    ("Red Bull 250ml",           "Beverages",      180, 120,   60, "006"),
    ("Stoney 500ml",             "Beverages",       65,  40,   80, "007"),
    ("Delmonte Juice 1L",        "Beverages",      140,  90,   75, "008"),

    # Dairy
    ("Brookside Milk 500ml",     "Dairy & Eggs",    75,  50,  180, "020"),
    ("KCC Butter 250g",          "Dairy & Eggs",   185, 130,   60, "021"),
    ("Fresha Yoghurt 250ml",     "Dairy & Eggs",    85,  55,  100, "022"),
    ("Egerton Eggs (tray 30)",   "Dairy & Eggs",   480, 360,   50, "023"),
    ("Tuzo Cheese 200g",         "Dairy & Eggs",   280, 190,   40, "024"),
    ("Molo Milk 1L",             "Dairy & Eggs",   135,  95,   90, "025"),

    # Bakery
    ("Supa Loaf White Bread",    "Bakery",           55,  35,  120, "030"),
    ("Family Bread Brown",       "Bakery",           60,  38,   80, "031"),
    ("Britania Digestive 200g",  "Bakery",          120,  80,   90, "032"),
    ("Kenchic Pilau Bun",        "Bakery",           25,  15,  200, "033"),
    ("Highlands Fruit Cake",     "Bakery",          350, 250,   30, "034"),

    # Grains
    ("Jogoo Maize Flour 2kg",    "Grains & Cereals", 170, 130,  200, "040"),
    ("Exe Long Grain Rice 2kg",  "Grains & Cereals", 310, 240,  150, "041"),
    ("Pembe Wheat Flour 2kg",    "Grains & Cereals", 200, 155,  120, "042"),
    ("Spaghetti 500g",           "Grains & Cereals",  90,  60,   80, "043"),
    ("Golden Morn Oats 500g",    "Grains & Cereals", 210, 155,   60, "044"),

    # Cooking Oils
    ("Elianto Oil 2L",           "Cooking Oils",    490, 380,   70, "050"),
    ("Soya Supreme Oil 1L",      "Cooking Oils",    280, 210,   80, "051"),
    ("Kimbo Cooking Fat 500g",   "Cooking Oils",    240, 180,   90, "052"),
    ("Zesta Ghee 400g",          "Cooking Oils",    360, 270,   45, "053"),

    # Meat
    ("Chicken Thighs 1kg",       "Meat & Poultry",  580, 450,   50, "060"),
    ("Beef Mince 500g",          "Meat & Poultry",  420, 330,   40, "061"),
    ("Farmer's Choice Sausages", "Meat & Poultry",  250, 180,   70, "062"),
    ("Chicken Breast 500g",      "Meat & Poultry",  380, 290,   55, "063"),

    # Fruits & Veg
    ("Tomatoes 1kg",             "Fruits & Veg",     80,  55,  200, "070"),
    ("Onions 1kg",               "Fruits & Veg",     70,  45,  180, "071"),
    ("Bananas (bunch)",          "Fruits & Veg",    100,  65,  120, "072"),
    ("Avocado (piece)",          "Fruits & Veg",     30,  18,  300, "073"),
    ("Capsicum 250g",            "Fruits & Veg",     60,  38,  150, "074"),
    ("Carrots 500g",             "Fruits & Veg",     45,  28,  160, "075"),

    # Household
    ("Omo Detergent 1kg",        "Household",       360, 270,  100, "080"),
    ("Jik Bleach 750ml",         "Household",       185, 130,   80, "081"),
    ("Colgate Toothpaste 100g",  "Household",       145, 100,  120, "082"),
    ("Dove Soap 135g",           "Household",       105,  70,  150, "083"),
    ("Always Pads Regular",      "Household",       165, 115,   90, "084"),
    ("Pampers Diapers S (10)",   "Household",       320, 240,   60, "085"),
    ("Toilet Paper 6-pack",      "Household",       290, 210,   80, "086"),
    ("Dettol 250ml",             "Household",       295, 215,   70, "087"),

    # Snacks
    ("Pringles Original 165g",   "Snacks & Confec", 380, 290,   50, "090"),
    ("KitKat 4-finger",          "Snacks & Confec", 110,  75,  100, "091"),
    ("Lay's Crisps 50g",         "Snacks & Confec",  80,  50,  150, "092"),
    ("Cadbury Dairy Milk 90g",   "Snacks & Confec", 220, 155,   80, "093"),
    ("Orbit Chewing Gum",        "Snacks & Confec",  60,  38,  200, "094"),
    ("Choco Pops 375g",          "Snacks & Confec", 410, 310,   55, "095"),

    # Baby
    ("NAN PRO Infant Formula",   "Baby & Kids",    1850,1400,   25, "100"),
    ("Pampers New Baby (24)",    "Baby & Kids",     650, 490,   30, "101"),
    ("Cerelac Wheat 200g",       "Baby & Kids",     480, 360,   40, "102"),
    ("Huggies Wipes 64s",        "Baby & Kids",     220, 155,   60, "103"),
    ("Johnson Baby Powder 200g", "Baby & Kids",     295, 215,   50, "104"),
    ("Enfamil A+ Stage 1 400g",  "Baby & Kids",    1650,1250,   20, "105"),
]

CUSTOMERS = [
    ("Alice Wanjiku",  "0712345001", "alice@email.com"),
    ("Brian Otieno",   "0723456002", "brian@email.com"),
    ("Christine Mwangi","0734567003", None),
    ("David Kamau",    "0745678004", "david@email.com"),
    ("Esther Achieng", "0756789005", None),
    ("Francis Njoroge","0767890006", "francis@email.com"),
    ("Grace Waithira", "0778901007", None),
    ("Hassan Omar",    "0789012008", "hassan@email.com"),
    ("Irene Adhiambo", "0790123009", None),
    ("James Mwenda",   "0701234010", "james@email.com"),
    ("Kariuki Muthoni","0712340011", None),
    ("Lucy Ndungu",    "0723451012", "lucy@email.com"),
    ("Michael Odhiambo","0734562013",None),
    ("Nancy Wambui",   "0745673014", "nancy@email.com"),
    ("Oliver Gitau",   "0756784015", None),
    ("Patricia Auma",  "0767895016", "patricia@email.com"),
    ("Quentin Muriuki","0778906017", None),
    ("Rose Njeri",     "0789017018", "rose@email.com"),
    ("Samuel Kipkoech","0790128019", None),
    ("Teresa Mutheu",  "0701239020", "teresa@email.com"),
]


# ─── Image utilities ──────────────────────────────────────────────────────────

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def collect_images(images_dir: str) -> list[Path]:
    """
    Walk the given directory and return all image file paths found.
    Works with both Windows paths (D:/...) and Linux paths.
    """
    p = Path(images_dir)
    if not p.exists():
        return []
    images = []
    for root, _dirs, files in os.walk(p):
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() in SUPPORTED_EXTS:
                images.append(fp)
    return images


def assign_image(product: Product, image_paths: list[Path], media_products_dir: Path):
    """
    Copy a randomly chosen image from image_paths into Django's
    media/products/ directory and assign it to the product.
    """
    if not image_paths:
        return

    src = random.choice(image_paths)
    dest_name = f"product_{product.id}_{src.name}"
    dest_path = media_products_dir / dest_name

    # Ensure destination directory exists
    media_products_dir.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(src, dest_path)
        with open(dest_path, "rb") as f:
            product.image.save(dest_name, File(f), save=True)
    except Exception as exc:
        print(f"      ⚠  Could not assign image for {product.name}: {exc}")


# ─── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed the database with realistic Mangunas supermarket data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--images-dir",
            type=str,
            default=r"D:\gadaf\Documents\Mkurugenzi – Merch_files",
            help="Path to folder containing product images",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing POS data before seeding",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n🛒  Mangunas POS — Seed Data\n"))

        # ── Optional clear ───────────────────────────────────────────────────
        if options["clear"]:
            self.stdout.write("  🗑  Clearing existing data…")
            StockMovement.objects.all().delete()
            Payment.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("     Done.\n"))

        # ── Collect images ───────────────────────────────────────────────────
        images_dir = options["images_dir"]
        image_paths = collect_images(images_dir)

        if image_paths:
            self.stdout.write(f"  🖼  Found {len(image_paths)} image(s) in: {images_dir}")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠  No images found in: {images_dir}\n"
                    f"     Products will be created without images.\n"
                    f"     Tip: Use --images-dir to set the correct path.\n"
                )
            )

        from django.conf import settings
        media_products_dir = Path(settings.MEDIA_ROOT) / "products"

        # ── Superuser ────────────────────────────────────────────────────────
        self.stdout.write("  👤  Creating superuser (admin / admin1234)…")
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                password="password123",
                email="admin@mangunas.co.ke",
                first_name="Admin",
                last_name="Mangunas",
            )
            self.stdout.write(self.style.SUCCESS("     Created."))
        else:
            self.stdout.write("     Already exists, skipping.")

        # ── Cashier ──────────────────────────────────────────────────────────
        cashier, _ = User.objects.get_or_create(
            username="cashier1",
            defaults=dict(
                password="pbkdf2_sha256$600000$cashier1",  # we set below
                first_name="Jane",
                last_name="Cashier",
                email="cashier1@mangunas.co.ke",
            ),
        )
        cashier.set_password("cashier1234")
        cashier.save()

        # ── Categories ───────────────────────────────────────────────────────
        self.stdout.write("\n  📂  Seeding categories…")
        cat_map: dict[str, Category] = {}
        for name, desc in CATEGORIES:
            cat, created = Category.objects.get_or_create(name=name, defaults={"description": desc})
            cat_map[name] = cat
            icon = "✔" if not created else "+"
            self.stdout.write(f"     {icon} {name}")

        # ── Products ─────────────────────────────────────────────────────────
        self.stdout.write("\n  📦  Seeding products…")
        product_objs: list[Product] = []
        for name, cat_name, price, cost, stock, bcode_sfx in PRODUCTS:
            barcode = f"5900000{bcode_sfx}"
            prod, created = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    barcode=barcode,
                    category=cat_map.get(cat_name),
                    price=Decimal(str(price)),
                    cost_price=Decimal(str(cost)),
                    stock_quantity=stock,
                    low_stock_threshold=10,
                    is_active=True,
                ),
            )
            product_objs.append(prod)

            # Assign image if we have some and the product has none yet
            if created or not prod.image:
                if image_paths:
                    assign_image(prod, image_paths, media_products_dir)
                    self.stdout.write(f"     + {name}  🖼")
                else:
                    self.stdout.write(f"     + {name}")
            else:
                self.stdout.write(f"     ✔ {name}  (exists)")

        # ── Customers ────────────────────────────────────────────────────────
        self.stdout.write("\n  👥  Seeding customers…")
        customer_objs: list[Customer] = []
        for cname, phone, email in CUSTOMERS:
            cust, created = Customer.objects.get_or_create(
                phone=phone,
                defaults=dict(
                    name=cname,
                    email=email,
                    loyalty_points=random.randint(0, 500),
                ),
            )
            customer_objs.append(cust)
            self.stdout.write(f"     {'+'  if created else '✔'} {cname}")

        # ── Sample Orders ────────────────────────────────────────────────────
        self.stdout.write("\n  🧾  Seeding sample orders…")

        if Order.objects.exists():
            self.stdout.write(self.style.WARNING("     Orders already exist — skipping. Use --clear to reset."))
        else:
            admin_user = User.objects.get(username="admin")

            for i in range(15):
                num_items = random.randint(1, 5)
                chosen_products = random.sample(product_objs, min(num_items, len(product_objs)))
                customer = random.choice(customer_objs + [None, None])

                # Retry up to 5 times in case of order_number collision
                order = None
                for attempt in range(5):
                    try:
                        order = Order.objects.create(
                            customer=customer,
                            cashier=admin_user,
                            status=Order.StatusChoices.PENDING,
                            discount_amount=Decimal("0.00"),
                        )
                        break
                    except Exception:
                        import time; time.sleep(0.05)

                if not order:
                    self.stdout.write(self.style.WARNING(f"     ⚠ Skipped order {i+1} after repeated collision"))
                    continue

                for prod in chosen_products:
                    qty = random.randint(1, 4)
                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        quantity=qty,
                        unit_price=prod.price,
                        discount=Decimal("0.00"),
                    )

                order.calculate_totals()

                pay_method = random.choice(["cash", "mpesa"])
                if pay_method == "cash":
                    tendered = order.total_amount + Decimal(str(random.choice([0, 50, 100, 200])))
                    Payment.objects.create(
                        order=order,
                        method=Payment.MethodChoices.CASH,
                        amount=order.total_amount,
                        status=Payment.StatusChoices.COMPLETED,
                        cash_tendered=tendered,
                        change_given=tendered - order.total_amount,
                    )
                else:
                    Payment.objects.create(
                        order=order,
                        method=Payment.MethodChoices.MPESA,
                        amount=order.total_amount,
                        status=Payment.StatusChoices.COMPLETED,
                        mpesa_phone=f"2547{random.randint(10000000, 99999999)}",
                        mpesa_receipt_number=f"TXN{random.randint(100000, 999999)}",
                        mpesa_transaction_date=timezone.now(),
                    )

                order.status = Order.StatusChoices.COMPLETED
                order.save()
                cname = customer.name if customer else "Walk-in"
                self.stdout.write(f"     + Order #{order.order_number}  ({cname})  KSh {order.total_amount}")

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f"\n  ✅  Seed complete!\n"
                f"     Categories : {Category.objects.count()}\n"
                f"     Products   : {Product.objects.count()}\n"
                f"     Customers  : {Customer.objects.count()}\n"
                f"     Orders     : {Order.objects.count()}\n\n"
                f"  🔑  Login credentials:\n"
                f"     Admin   → username: admin      password: admin1234\n"
                f"     Cashier → username: cashier1   password: cashier1234\n"
            )
        )