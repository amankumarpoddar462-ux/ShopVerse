import os
import logging

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.core.exceptions import ImproperlyConfigured, ValidationError
from PIL import Image, UnidentifiedImageError


MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
logger = logging.getLogger(__name__)


def _configure_cloudinary():
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
            'CLOUDINARY_API_SECRET (or CLOUDINARY_URL) before uploading product images.'
        )


def validate_product_image(uploaded_file):
    if hasattr(uploaded_file, 'size'):
        file_size = uploaded_file.size
    else:
        current_position = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(current_position)

    if file_size > MAX_PRODUCT_IMAGE_SIZE:
        raise ValidationError('Each product image must be no larger than 5 MB.')

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError('Use a JPEG, PNG, WEBP, or GIF product image.')
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ValidationError('Choose a valid image file.') from exc
    finally:
        uploaded_file.seek(0)


def upload_product_images(uploaded_files, folder):
    uploaded_files = list(uploaded_files)
    if not uploaded_files:
        return []
    _configure_cloudinary()
    uploaded_assets = []
    try:
        for uploaded_file in uploaded_files:
            uploaded_file.seek(0)
            result = cloudinary.uploader.upload(
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
                cloudinary.uploader.destroy(asset['public_id'], resource_type='image')
            except CloudinaryError:
                logger.exception('Failed to clean up incomplete Cloudinary upload %s.', asset['public_id'])
        raise
    return uploaded_assets


def delete_product_image(public_id):
    if not public_id:
        return
    _configure_cloudinary()
    result = cloudinary.uploader.destroy(
        public_id,
        resource_type='image',
        invalidate=True,
    )
    if result.get('result') not in {'ok', 'not found'}:
        raise CloudinaryError(f"Cloudinary could not delete image {public_id!r}.")
