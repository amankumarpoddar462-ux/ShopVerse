import base64
import binascii
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.image_storage import upload_product_images, validate_product_image
from products.models import Product
from reviews.models import Review


def local_image_file(image_url):
    if image_url.startswith('data:image/'):
        header, separator, encoded_data = image_url.partition(',')
        if not separator or ';base64' not in header:
            raise CommandError('Encountered an unsupported embedded product image.')
        extension = header.split('/', 1)[1].split(';', 1)[0]
        try:
            image_data = base64.b64decode(encoded_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CommandError('Encountered invalid embedded product image data.') from exc
        return ContentFile(image_data, name=f'legacy-product-image.{extension}')

    image_path = unquote(urlparse(image_url).path)
    media_url = settings.MEDIA_URL
    if not image_path.startswith(media_url):
        return None
    relative_path = image_path[len(media_url):]
    media_root = Path(settings.MEDIA_ROOT).resolve()
    source_path = (media_root / relative_path).resolve()
    if media_root not in source_path.parents:
        raise CommandError('A product image path resolves outside MEDIA_ROOT.')
    if not source_path.is_file():
        return None
    return source_path.open('rb')


class Command(BaseCommand):
    help = 'Move legacy local and embedded product and review images to Cloudinary.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='List eligible images without uploading.')
        parser.add_argument('--limit', type=int, help='Stop after processing this many products.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        products = Product.objects.all().order_by('id')
        if options['limit']:
            products = products[:options['limit']]

        migrated = 0
        for product in products:
            if product.main_image_url and not product.main_image_public_id:
                migrated += self.migrate_image(
                    product,
                    product.main_image_url,
                    'main_image',
                    dry_run,
                )
            for image in product.gallery_images.filter(public_id='').order_by('id'):
                migrated += self.migrate_image(
                    image,
                    image.image_url,
                    'gallery_image',
                    dry_run,
                )
        for review in Review.objects.all().order_by('id'):
            review_urls = [
                (review.photo_url_1, review.photo_public_id_1, 'photo_url_1'),
                (review.photo_url_2, review.photo_public_id_2, 'photo_url_2'),
                (review.photo_url_3, review.photo_public_id_3, 'photo_url_3'),
            ]
            for image_url, public_id, url_field in review_urls:
                if image_url and not public_id:
                    migrated += self.migrate_image(
                        review,
                        image_url,
                        url_field,
                        dry_run,
                    )
        self.stdout.write(self.style.SUCCESS(
            f'{"Would migrate" if dry_run else "Migrated"} product/review image(s). '
            'Non-local URLs and missing files were skipped.'
        ))

    def migrate_image(self, instance, image_url, kind, dry_run):
        if 'res.cloudinary.com' in image_url:
            return 0
        source_file = local_image_file(image_url)
        if source_file is None:
            return 0

        try:
            validate_product_image(source_file)
            if dry_run:
                self.stdout.write(f'Eligible {kind}: {instance.pk}')
                return 1
            if isinstance(instance, Product):
                product = instance
            elif hasattr(instance, 'product'):
                product = instance.product
            else:
                product = instance
            asset = upload_product_images(
                [source_file],
                folder=(
                    f'shopverse/reviews/customer_{instance.customer_id}'
                    if kind.startswith('photo_url_')
                    else f'shopverse/products/seller_{product.seller_id}'
                ),
            )[0]
            with transaction.atomic():
                if kind == 'main_image':
                    instance.main_image_url = asset['url']
                    instance.main_image_public_id = asset['public_id']
                    instance.save(update_fields=['main_image_url', 'main_image_public_id'])
                elif kind == 'gallery_image':
                    instance.image_url = asset['url']
                    instance.public_id = asset['public_id']
                    instance.save(update_fields=['image_url', 'public_id'])
                else:
                    setattr(instance, kind, asset['url'])
                    public_id_field = kind.replace('photo_url_', 'photo_public_id_')
                    setattr(instance, public_id_field, asset['public_id'])
                    instance.save(update_fields=[kind, public_id_field])
            self.stdout.write(self.style.SUCCESS(f'Migrated {kind}: {instance.pk}'))
            return 1
        finally:
            source_file.close()
