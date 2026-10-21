import os
import logging

try:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.exceptions import Error as CloudinaryError
except ImportError:  # pragma: no cover - fallback for environments without Cloudinary.
    cloudinary = None
    CloudinaryError = Exception
    cloudinary_uploader = None
else:
    cloudinary_uploader = cloudinary.uploader
from django.core.exceptions import ImproperlyConfigured, ValidationError
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
logger = logging.getLogger(__name__)


def _configure_cloudinary():
    if cloudinary is None:
        raise ImproperlyConfigured(
            'Cloudinary is not installed. Install the cloudinary package or set up the required image service.'
        )
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
    config = cloudinary.config()
    if not config.cloud_name or not config.api_key or not config.api_secret:
        raise ImproperlyConfigured(
            'Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and '
            'CLOUDINARY_API_SECRET (or CLOUDINARY_URL) before uploading images.'
        )


def validate_image_upload(uploaded_file, image_label='image'):
    if hasattr(uploaded_file, 'size'):
        file_size = uploaded_file.size
    else:
        current_position = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(current_position)

    if file_size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError(f'Each {image_label} must be no larger than 5 MB.')

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError(f'Use a JPEG, PNG, WEBP, or GIF {image_label}.')
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ValidationError('Choose a valid image file.') from exc
    finally:
        uploaded_file.seek(0)


def validate_product_image(uploaded_file):
    validate_image_upload(uploaded_file, image_label='product image')


def upload_images_to_cloudinary(uploaded_files, folder):
    uploaded_files = list(uploaded_files)
    if not uploaded_files:
        return []
    _configure_cloudinary()
    uploaded_assets = []
    try:
        for uploaded_file in uploaded_files:
            uploaded_file.seek(0)
            result = cloudinary_uploader.upload(
                uploaded_file,
                folder=folder,
                resource_type='image',
                use_filename=True,
                unique_filename=True,
            )
            uploaded_assets.append({
                'url': result['secure_url'],
                'public_id': result['public_id'],
            })
    except CloudinaryError:
        for asset in uploaded_assets:
            try:
                cloudinary_uploader.destroy(asset['public_id'], resource_type='image')
            except CloudinaryError:
                logger.exception('Failed to clean up incomplete Cloudinary upload %s.', asset['public_id'])
        raise
    return uploaded_assets


def upload_product_images(uploaded_files, folder):
    return upload_images_to_cloudinary(uploaded_files, folder)


def delete_cloudinary_image(public_id):
    if not public_id:
        return
    _configure_cloudinary()
    result = cloudinary_uploader.destroy(
        public_id,
        resource_type='image',
        invalidate=True,
    )
    if result.get('result') not in {'ok', 'not found'}:
        raise CloudinaryError(f"Cloudinary could not delete image {public_id!r}.")


def delete_product_image(public_id):
    delete_cloudinary_image(public_id)
