from django.core.management.base import BaseCommand
from apps.marketplace.models import Product, ProductImage

MAPPINGS = {
    'a1b2c3d4-0001-0001-0001-000000000001': 'Organic carrots.jpg',
    'a1b2c3d4-0001-0001-0001-000000000002': 'Organic tomatoes.jpeg',
    'a1b2c3d4-0001-0001-0001-000000000003': 'Courgettes.webp',
    'a1b2c3d4-0001-0001-0001-000000000004': 'Salad potatoes.jpg',
    'a1b2c3d4-0001-0001-0001-000000000005': 'Red onions.webp',
    'a1b2c3d4-0001-0001-0001-000000000006': 'Organic lettuce.jpeg',
    'a1b2c3d4-0001-0001-0001-000000000007': 'Stored potatoes.jpg',
    'a1b2c3d4-0001-0001-0001-000000000008': 'Mixed salad leaves.jpg',
    'a1b2c3d4-0001-0001-0001-000000000009': 'Buttternut squash.jpg',
    'a1b2c3d4-0001-0001-0001-000000000010': 'Fresh apples.webp',
    'a1b2c3d4-0001-0001-0001-000000000011': 'Strawberry.jpeg',
    'a1b2c3d4-0001-0001-0001-000000000012': 'conference-pear-variet.jpg',
    'a1b2c3d4-0001-0001-0001-000000000013': 'Organic free range eggs.jpg',
    'a1b2c3d4-0001-0001-0001-000000000014': 'Fresh whole milk.webp',
    'a1b2c3d4-0001-0001-0001-000000000015': 'Mature cheddar cheese.jpg',
    'a1b2c3d4-0001-0001-0001-000000000016': 'Natural yoghurt.jpg',
    'a1b2c3d4-0001-0001-0001-000000000017': 'Double cream.jpg',
    'a1b2c3d4-0001-0001-0001-000000000018': 'Soft goat cheese.jpg',
    'a1b2c3d4-0001-0001-0001-000000000019': 'Walnut bread.jpg',
    'a1b2c3d4-0001-0001-0001-000000000020': 'Sourdough loaf.jpg',
    'a1b2c3d4-0001-0001-0001-000000000021': 'Seeded batch loaf.jpg',
    'a1b2c3d4-0001-0001-0001-000000000022': 'Blueberry muffins.jpg',
    'a1b2c3d4-0001-0001-0001-000000000023': 'Strawberry jam.jpg',
    'a1b2c3d4-0001-0001-0001-000000000024': 'Apple chutney.jpg',
    'a1b2c3d4-0001-0001-0001-000000000025': 'wildflower honey.jpg',
    'a1b2c3d4-0001-0001-0001-000000000026': 'pork sausage.jpg',
    'a1b2c3d4-0001-0001-0001-000000000027': 'free range chicken.jpg',
    'a1b2c3d4-0001-0001-0001-000000000028': 'Purple Sprouting Broccoli.jpg',
    'a1b2c3d4-0001-0001-0001-000000000029': 'pumpkin.jpg',
}

class Command(BaseCommand):
    help = 'Replace product images with local PNG static files'

    def handle(self, *args, **kwargs):
        for product_id, filename in MAPPINGS.items():
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                self.stdout.write(f'SKIP (not found): {product_id}')
                continue

            # Delete existing images for this product
            deleted, _ = ProductImage.objects.filter(product=product).delete()

            # Insert new image
            ProductImage.objects.create(
                product=product,
                url=f'/static/png/{filename}',
            )
            self.stdout.write(f'OK: {product.name} → {filename} (removed {deleted} old)')