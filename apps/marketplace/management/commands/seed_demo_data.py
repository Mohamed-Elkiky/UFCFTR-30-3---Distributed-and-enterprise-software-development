"""
Generate comprehensive demo data for all 25 test cases.

Run inside Docker after loaddata:
    docker compose exec web python manage.py seed_demo_data

Safe to run multiple times — skips records that already exist.
All demo accounts use password: BrfnDemo2026!
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

DEMO_PASSWORD = "BrfnDemo2026!"


def _uuid(short):
    """Deterministic UUID from a short label so reruns are idempotent."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"brfn-demo-{short}")


class Command(BaseCommand):
    help = "Seed comprehensive demo data for all 25 test cases."

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.accounts.models import (
            ProducerProfile, CustomerProfile,
            CommunityGroupProfile, RestaurantProfile,
        )
        from apps.marketplace.models import (
            Product, ProductCategory, SurplusDeal,
        )
        from apps.orders.models import (
            CustomerOrder, ProducerOrder, OrderItem, OrderStatusHistory,
        )
        from apps.payments.models import (
            CommissionPolicy, PaymentTransaction, OrderCommission,
            SettlementWeek, ProducerSettlement, ProducerOrderSettlementLink,
        )
        from apps.reviews.models import ProductReview
        from apps.content.models import ContentPost, ContentProductLink

        User = get_user_model()
        today = date.today()
        now = timezone.now()

        self.stdout.write("\n=== BRFN Demo Data Seeder ===\n")

        # ─────────────────────────────────────────
        # 1. USERS & PROFILES (TC-001, TC-002, TC-017, TC-018, TC-022)
        # ─────────────────────────────────────────
        self.stdout.write("Creating users & profiles...")

        # Customers
        robert, _ = User.objects.get_or_create(
            email="robert.johnson@email.com",
            defaults={"role": "customer", "phone": "+447700900123"},
        )
        robert.set_password(DEMO_PASSWORD)
        robert.save()
        CustomerProfile.objects.update_or_create(
            user=robert,
            defaults={
                "full_name": "Robert Johnson",
                "street": "45 Park Street",
                "city": "Bristol",
                "state": "Avon",
                "postcode": "BS1 5JG",
                "country": "United Kingdom",
                "latitude": Decimal("51.453700"),
                "longitude": Decimal("-2.596600"),
            },
        )

        emily, _ = User.objects.get_or_create(
            email="emily.chen@email.com",
            defaults={"role": "customer", "phone": "+447700900456"},
        )
        emily.set_password(DEMO_PASSWORD)
        emily.save()
        CustomerProfile.objects.update_or_create(
            user=emily,
            defaults={
                "full_name": "Emily Chen",
                "street": "12 Queens Road",
                "city": "Bristol",
                "state": "Avon",
                "postcode": "BS8 1QU",
                "country": "United Kingdom",
                "latitude": Decimal("51.456200"),
                "longitude": Decimal("-2.610800"),
            },
        )

        # Reset password on existing test customer too
        test_cust = User.objects.filter(email="test@test.com").first()
        if test_cust:
            test_cust.set_password(DEMO_PASSWORD)
            test_cust.save()

        # Community Group (TC-017)
        stmarys, _ = User.objects.get_or_create(
            email="catering@stmarys-school.org.uk",
            defaults={"role": "community_group", "phone": "+441179001234"},
        )
        stmarys.set_password(DEMO_PASSWORD)
        stmarys.save()
        CommunityGroupProfile.objects.update_or_create(
            user=stmarys,
            defaults={
                "organisation_name": "St. Mary's School",
                "organisation_type": "school",
                "contact_name": "Sarah Williams",
                "delivery_address": "15 College Road, Bristol",
                "postcode": "BS3 1QR",
            },
        )
        # Community groups also need a CustomerProfile to place orders
        CustomerProfile.objects.update_or_create(
            user=stmarys,
            defaults={
                "full_name": "St. Mary's School",
                "street": "15 College Road",
                "city": "Bristol",
                "state": "Avon",
                "postcode": "BS3 1QR",
                "country": "United Kingdom",
                "latitude": Decimal("51.440100"),
                "longitude": Decimal("-2.596300"),
            },
        )

        # Restaurant (TC-018)
        clifton, _ = User.objects.get_or_create(
            email="info@cliftonkitchen.co.uk",
            defaults={"role": "restaurant", "phone": "+441179005678"},
        )
        clifton.set_password(DEMO_PASSWORD)
        clifton.save()
        RestaurantProfile.objects.update_or_create(
            user=clifton,
            defaults={
                "restaurant_name": "The Clifton Kitchen",
                "contact_name": "James Cooper",
                "delivery_address": "8 The Mall, Clifton, Bristol",
                "postcode": "BS8 4AA",
            },
        )
        CustomerProfile.objects.update_or_create(
            user=clifton,
            defaults={
                "full_name": "The Clifton Kitchen",
                "street": "8 The Mall, Clifton",
                "city": "Bristol",
                "state": "Avon",
                "postcode": "BS8 4AA",
                "country": "United Kingdom",
                "latitude": Decimal("51.464100"),
                "longitude": Decimal("-2.621500"),
            },
        )

        # Reset passwords on all existing producers & admin
        for u in User.objects.filter(role__in=["producer", "admin"]):
            u.set_password(DEMO_PASSWORD)
            u.save()

        self.stdout.write(self.style.SUCCESS("  Users & profiles ready."))

        # ─────────────────────────────────────────
        # 2. UPDATE PRODUCTS (TC-016 seasonal, TC-023 thresholds)
        # ─────────────────────────────────────────
        self.stdout.write("Updating product seasonal data & thresholds...")

        seasonal_updates = {
            "Strawberries": (6, 8),       # June-August
            "Organic Tomatoes": (5, 10),  # May-October
            "Courgettes": (6, 9),         # June-September
            "Organic Lettuce": (4, 10),   # April-October
            "Mixed Salad Leaves": (4, 10),
            "Purple Sprouting Broccoli": (2, 4),  # Feb-April
            "Pumpkin": (9, 11),           # Sep-November
            "Organic Carrots": (6, 11),   # June-November
        }
        for name, (start, end) in seasonal_updates.items():
            Product.objects.filter(name=name).update(
                seasonal_start_month=start, seasonal_end_month=end
            )

        # Set varied low stock thresholds
        Product.objects.filter(name="Organic Free Range Eggs").update(
            low_stock_threshold=10, stock_qty=50
        )
        Product.objects.filter(name="Fresh Whole Milk").update(
            low_stock_threshold=15, stock_qty=80
        )
        Product.objects.filter(name="Sourdough Loaf").update(
            low_stock_threshold=5, stock_qty=18
        )

        # Ensure best_before_dates are in the future for demo ordering
        future = today + timedelta(days=14)
        Product.objects.filter(
            best_before_date__isnull=False, best_before_date__lt=today
        ).update(best_before_date=future)
        # Also set best_before on perishables that lack it
        for name in ["Fresh Whole Milk", "Natural Yoghurt", "Double Cream",
                      "Organic Free Range Eggs", "Organic Lettuce"]:
            Product.objects.filter(name=name, best_before_date__isnull=True).update(
                best_before_date=future
            )

        self.stdout.write(self.style.SUCCESS("  Products updated."))

        # ─────────────────────────────────────────
        # 3. ORDERS — diverse, multi-vendor, varied statuses
        #    (TC-007, TC-008, TC-009, TC-010, TC-012, TC-021, TC-025)
        # ─────────────────────────────────────────
        self.stdout.write("Creating orders...")

        robert_cp = robert.customer_profile
        emily_cp = emily.customer_profile

        # Helper to look up products
        def prod(name):
            return Product.objects.filter(name=name).first()

        # Helper to build a complete order
        def make_order(customer_profile, items_spec, delivery_offset_days,
                       status="delivered", special="", order_label=""):
            oid = _uuid(f"order-{order_label}")
            d_date = today + timedelta(days=delivery_offset_days)
            subtotal = sum(p.price_pence * qty for p, qty in items_spec)
            commission = round(subtotal * 0.05)
            total = subtotal + commission

            co, created = CustomerOrder.objects.get_or_create(
                id=oid,
                defaults={
                    "customer": customer_profile,
                    "delivery_address": f"{customer_profile.street}, {customer_profile.city}",
                    "delivery_postcode": customer_profile.postcode,
                    "delivery_date": d_date,
                    "special_instructions": special,
                    "subtotal_pence": subtotal,
                    "commission_pence": commission,
                    "total_pence": total,
                    "status": status,
                },
            )
            if not created:
                return co  # Already exists, skip

            # Group items by producer
            producer_items = {}
            for product, qty in items_spec:
                pid = product.producer_id
                producer_items.setdefault(pid, []).append((product, qty))

            for pid, pitems in producer_items.items():
                p_sub = sum(pr.price_pence * q for pr, q in pitems)
                p_comm = round(p_sub * 0.05)
                po_id = _uuid(f"po-{order_label}-{pid}")
                po, _ = ProducerOrder.objects.get_or_create(
                    id=po_id,
                    defaults={
                        "customer_order": co,
                        "producer_id": pid,
                        "subtotal_pence": p_sub,
                        "commission_pence": p_comm,
                        "producer_payment_pence": p_sub - p_comm,
                        "status": status,
                        "delivery_date": d_date,
                    },
                )
                for product, qty in pitems:
                    OrderItem.objects.get_or_create(
                        id=_uuid(f"oi-{order_label}-{product.pk}"),
                        defaults={
                            "order": co,
                            "product": product,
                            "product_name": product.name,
                            "product_unit": product.unit,
                            "price_pence": product.price_pence,
                            "quantity": qty,
                            "line_total_pence": product.price_pence * qty,
                        },
                    )

                # Status history for delivered orders
                if status == "delivered":
                    for i, (old_s, new_s) in enumerate([
                        ("pending", "confirmed"),
                        ("confirmed", "ready"),
                        ("ready", "delivered"),
                    ]):
                        OrderStatusHistory.objects.get_or_create(
                            id=_uuid(f"sh-{order_label}-{pid}-{i}"),
                            defaults={
                                "producer_order": po,
                                "old_status": old_s,
                                "new_status": new_s,
                                "notes": "",
                            },
                        )

            # Payment transaction
            PaymentTransaction.objects.get_or_create(
                id=_uuid(f"pay-{order_label}"),
                defaults={
                    "customer_order": co,
                    "provider": "mock",
                    "provider_ref": f"MOCK-{order_label.upper()}",
                    "status": "captured",
                    "amount_pence": total,
                },
            )

            # Commission record
            policy = CommissionPolicy.objects.first()
            if policy:
                OrderCommission.objects.get_or_create(
                    id=_uuid(f"comm-{order_label}"),
                    defaults={
                        "customer_order": co,
                        "commission_policy": policy,
                        "gross_pence": subtotal,
                        "commission_pence": commission,
                        "net_pence": subtotal - commission,
                    },
                )

            return co

        # ── Robert's orders (3 delivered + 1 pending) ──
        carrots = prod("Organic Carrots")
        milk = prod("Fresh Whole Milk")
        eggs = prod("Organic Free Range Eggs")
        bread = prod("Sourdough Loaf")
        cheese = prod("Mature Cheddar Cheese")
        honey = prod("Wildflower Honey")
        jam = prod("Strawberry Jam")
        apples = prod("Fresh Apples")
        lettuce = prod("Organic Lettuce")
        sausages = prod("Pork Sausages")

        # Order 1: single producer (Bristol Valley Farm) — delivered 2 weeks ago
        make_order(robert_cp,
            [(carrots, 3), (lettuce, 2)],
            delivery_offset_days=-14, status="delivered", order_label="rob-1")

        # Order 2: multi-vendor (Hillside Dairy + Severn Valley Bakers) — delivered 1 week ago
        make_order(robert_cp,
            [(milk, 2), (cheese, 1), (bread, 1)],
            delivery_offset_days=-7, status="delivered", order_label="rob-2")

        # Order 3: multi-vendor (3 producers) — delivered 5 days ago
        make_order(robert_cp,
            [(eggs, 2), (honey, 1), (apples, 3)],
            delivery_offset_days=-5, status="delivered", order_label="rob-3")

        # Order 4: pending order due in 3 days
        make_order(robert_cp,
            [(carrots, 2), (milk, 1), (bread, 2)],
            delivery_offset_days=3, status="pending", order_label="rob-4")

        # ── Emily's orders (2 delivered + 1 confirmed) ──
        make_order(emily_cp,
            [(cheese, 2), (jam, 1), (sausages, 1)],
            delivery_offset_days=-10, status="delivered", order_label="emily-1")

        make_order(emily_cp,
            [(carrots, 5), (apples, 4), (honey, 2)],
            delivery_offset_days=-3, status="delivered", order_label="emily-2")

        make_order(emily_cp,
            [(eggs, 3), (lettuce, 2)],
            delivery_offset_days=4, status="confirmed", order_label="emily-3")

        # ── St Mary's bulk order (TC-017) — delivered ──
        stmarys_cp = stmarys.customer_profile
        potatoes = prod("Stored Potatoes")
        make_order(stmarys_cp,
            [(potatoes, 50), (milk, 30), (carrots, 20)],
            delivery_offset_days=-6, status="delivered",
            special="Delivery to kitchen entrance, contact kitchen manager",
            order_label="stmarys-1")

        # ── Clifton Kitchen order (TC-018) — delivered ──
        clifton_cp = clifton.customer_profile
        make_order(clifton_cp,
            [(carrots, 10), (lettuce, 8), (cheese, 5), (bread, 6)],
            delivery_offset_days=-4, status="delivered",
            order_label="clifton-1")

        self.stdout.write(self.style.SUCCESS("  Orders created."))

        # ─────────────────────────────────────────
        # 4. RECURRING ORDER TEMPLATE (TC-018)
        # ─────────────────────────────────────────
        self.stdout.write("Creating recurring order template...")
        from apps.orders.models import RecurringOrderTemplate, RecurringOrderItem

        rot, _ = RecurringOrderTemplate.objects.get_or_create(
            id=_uuid("recurring-clifton"),
            defaults={
                "customer": clifton_cp,
                "name": "Weekly Kitchen Supplies",
                "rrule": "FREQ=WEEKLY;BYDAY=MO",
                "active": True,
            },
        )
        for product, qty in [(carrots, 10), (lettuce, 8), (cheese, 5), (bread, 6)]:
            if product:
                RecurringOrderItem.objects.get_or_create(
                    template=rot,
                    product=product,
                    defaults={"quantity": qty},
                )

        self.stdout.write(self.style.SUCCESS("  Recurring template ready."))

        # ─────────────────────────────────────────
        # 5. SETTLEMENTS (TC-012, TC-025)
        # ─────────────────────────────────────────
        self.stdout.write("Creating settlement data...")

        week1_start = today - timedelta(days=today.weekday() + 7)  # Last Monday
        week2_start = week1_start - timedelta(days=7)

        for wk_start, label in [(week1_start, "wk1"), (week2_start, "wk2")]:
            sw, _ = SettlementWeek.objects.get_or_create(
                id=_uuid(f"sw-{label}"),
                defaults={
                    "week_start": wk_start,
                    "week_end": wk_start + timedelta(days=6),
                },
            )
            # Create producer settlements for producers with delivered orders in that week
            delivered_pos = ProducerOrder.objects.filter(
                status="delivered",
                delivery_date__gte=wk_start,
                delivery_date__lte=wk_start + timedelta(days=6),
            )
            producers_in_week = set()
            for po in delivered_pos:
                if po.producer_id and po.producer_id not in producers_in_week:
                    producers_in_week.add(po.producer_id)
                    ps, _ = ProducerSettlement.objects.get_or_create(
                        id=_uuid(f"ps-{label}-{po.producer_id}"),
                        defaults={
                            "settlement_week": sw,
                            "producer_id": po.producer_id,
                            "commission_pence": po.commission_pence,
                            "payout_pence": po.producer_payment_pence,
                            "status": "processed" if label == "wk2" else "pending",
                        },
                    )
                    ProducerOrderSettlementLink.objects.get_or_create(
                        producer_order=po,
                        producer_settlement=ps,
                    )

        self.stdout.write(self.style.SUCCESS("  Settlements created."))

        # ─────────────────────────────────────────
        # 6. REVIEWS (TC-024)
        # ─────────────────────────────────────────
        self.stdout.write("Creating reviews...")

        reviews_data = [
            (robert_cp, carrots, 5, "Excellent quality",
             "Incredibly fresh and flavourful. Perfect for our family salads."),
            (robert_cp, milk, 4, "Great local milk",
             "Creamy and fresh, delivered on time. Will order again."),
            (emily_cp, cheese, 5, "Best cheddar in Bristol",
             "Rich, mature flavour. Beats anything from the supermarket."),
            (emily_cp, honey, 5, "Beautiful wildflower honey",
             "Wonderful floral notes. Perfect on toast and in tea."),
            (robert_cp, eggs, 4, "Lovely free range eggs",
             "Rich yolks, great for baking. Consistent quality."),
        ]
        for cp, product, stars, title, body in reviews_data:
            if product:
                ProductReview.objects.get_or_create(
                    id=_uuid(f"review-{cp.pk}-{product.pk}"),
                    defaults={
                        "product": product,
                        "customer": cp,
                        "stars": stars,
                        "title": title,
                        "body": body,
                    },
                )

        self.stdout.write(self.style.SUCCESS("  Reviews created."))

        # ─────────────────────────────────────────
        # 7. CONTENT — recipes, farm stories, storage guides (TC-020)
        # ─────────────────────────────────────────
        self.stdout.write("Creating content posts...")

        bvf = ProducerProfile.objects.filter(business_name="Bristol Valley Farm").first()
        hd = ProducerProfile.objects.filter(business_name="Hillside Dairy").first()
        svb = ProducerProfile.objects.filter(business_name="Severn Valley Bakers").first()

        posts = [
            (bvf, "recipe", "Roasted Root Vegetable Medley",
             "A hearty autumn dish featuring our organic carrots, parsnips and potatoes. "
             "Toss with olive oil, rosemary and garlic. Roast at 200C for 40 minutes. "
             "Finish with a drizzle of local honey for a caramelised glaze.",
             "autumn", [carrots, potatoes, honey]),
            (bvf, "farm_story", "Spring Planting at Bristol Valley Farm",
             "This week we started planting our early season lettuces and salad leaves. "
             "The mild Bristol spring means we can get a head start on the season. "
             "We use companion planting with marigolds to keep pests away naturally.",
             "spring", [lettuce]),
            (hd, "storage_guide", "How to Store Dairy Products",
             "Keep milk at 1-4C and use within 3 days of delivery for best freshness. "
             "Hard cheeses like our cheddar can be wrapped in wax paper and refrigerated "
             "for up to 2 weeks. Yoghurt keeps well sealed for 5-7 days.",
             "all_year", [milk, cheese]),
            (svb, "recipe", "Perfect Sourdough Toast with Local Honey",
             "Slice our sourdough thick (2cm), toast until golden. "
             "Spread with good butter and drizzle with Hartcliffe wildflower honey. "
             "A simple breakfast that showcases the best of Bristol produce.",
             "all_year", [bread, honey]),
        ]

        for producer, kind, title, body, season, products in posts:
            if producer:
                cp_obj, _ = ContentPost.objects.get_or_create(
                    id=_uuid(f"content-{title[:20]}"),
                    defaults={
                        "producer": producer,
                        "kind": kind,
                        "title": title,
                        "body": body,
                        "seasonal_tag": season,
                        "is_published": True,
                    },
                )
                for p in products:
                    if p:
                        ContentProductLink.objects.get_or_create(
                            content=cp_obj, product=p
                        )

        self.stdout.write(self.style.SUCCESS("  Content created."))

        # ─────────────────────────────────────────
        # 8. SURPLUS DEALS (TC-019)
        # ─────────────────────────────────────────
        self.stdout.write("Creating surplus deals...")

        surplus_data = [
            (lettuce, 3000, 48, "Perfect condition, harvest fresh — must sell to avoid waste."),
            (apples, 2000, 72, "Slight cosmetic blemishes but great flavour. Ideal for cooking."),
        ]
        for product, discount_bp, hours, note in surplus_data:
            if product:
                SurplusDeal.objects.update_or_create(
                    product=product,
                    defaults={
                        "discount_bp": discount_bp,
                        "expires_at": now + timedelta(hours=hours),
                        "note": note,
                    },
                )

        self.stdout.write(self.style.SUCCESS("  Surplus deals created."))

        # ─────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n=== Demo data seeding complete! ==="))
        self.stdout.write(f"  All accounts use password: {DEMO_PASSWORD}")
        self.stdout.write(f"  Run 'python manage.py dumpdata --indent 2 > fixtures/seed.json' to export.\n")