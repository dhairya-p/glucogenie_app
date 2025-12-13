"""Supabase Storage service for uploading meal images."""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from PIL import Image
from supabase import Client

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Configuration
STORAGE_BUCKET = "meal-images"
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_WIDTH = 1024  # Resize images to max 1024px width for efficiency
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


class ImageUploadError(Exception):
    """Custom exception for image upload errors."""
    pass


def _resize_image(image_bytes: bytes, max_width: int = MAX_IMAGE_WIDTH) -> bytes:
    """Resize image to max width while maintaining aspect ratio.

    Args:
        image_bytes: Original image bytes
        max_width: Maximum width in pixels

    Returns:
        Resized image bytes in JPEG format
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert RGBA to RGB if needed (for PNG with transparency)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Resize if width exceeds max_width
        if img.width > max_width:
            aspect_ratio = img.height / img.width
            new_height = int(max_width * aspect_ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {img.width}x{img.height} to {max_width}x{new_height}")

        # Convert to JPEG and compress
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        output.seek(0)

        return output.getvalue()
    except Exception as exc:
        logger.error(f"Error resizing image: {exc}", exc_info=True)
        # Return original bytes if resize fails
        return image_bytes


def upload_meal_image(
    file_content: bytes,
    filename: str,
    user_id: str,
    resize: bool = True,
) -> str:
    """Upload a meal image to Supabase Storage and return the public URL.

    Args:
        file_content: Image file content as bytes
        filename: Original filename
        user_id: User ID for organizing files
        resize: Whether to resize the image before uploading

    Returns:
        Public URL of the uploaded image

    Raises:
        ImageUploadError: If upload fails
    """
    try:
        # Validate file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise ImageUploadError(
                f"Invalid file extension: {file_ext}. "
                f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Validate file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > MAX_IMAGE_SIZE_MB:
            raise ImageUploadError(
                f"File too large: {file_size_mb:.2f}MB. Max size: {MAX_IMAGE_SIZE_MB}MB"
            )

        # Resize image if requested
        if resize:
            try:
                file_content = _resize_image(file_content)
                file_ext = ".jpg"  # Always save as JPEG after resize
            except Exception as exc:
                logger.warning(f"Image resize failed, uploading original: {exc}")

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        storage_path = f"{user_id}/{timestamp}_{unique_id}{file_ext}"

        # Upload to Supabase Storage
        supabase = get_supabase_client()

        logger.info(f"Uploading image to {STORAGE_BUCKET}/{storage_path}")

        # Upload file
        result = supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": f"image/{file_ext.replace('.', '')}"}
        )

        # Get public URL
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        logger.info(f"Image uploaded successfully: {public_url}")
        return public_url

    except ImageUploadError:
        raise
    except Exception as exc:
        logger.error(f"Error uploading image to Supabase Storage: {exc}", exc_info=True)
        raise ImageUploadError(f"Failed to upload image: {str(exc)}") from exc


def delete_meal_image(image_url: str, user_id: str) -> bool:
    """Delete a meal image from Supabase Storage.

    Args:
        image_url: Public URL of the image
        user_id: User ID for verification

    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        # Extract storage path from URL
        # URL format: https://.../storage/v1/object/public/meal-images/{user_id}/{filename}
        if STORAGE_BUCKET not in image_url:
            logger.error(f"Invalid image URL: {image_url}")
            return False

        # Extract path after bucket name
        parts = image_url.split(f"{STORAGE_BUCKET}/")
        if len(parts) < 2:
            logger.error(f"Could not extract path from URL: {image_url}")
            return False

        storage_path = parts[1]

        # Verify user_id matches
        if not storage_path.startswith(user_id):
            logger.error(f"User ID mismatch for deletion: {user_id} vs {storage_path}")
            return False

        # Delete from storage
        supabase = get_supabase_client()
        supabase.storage.from_(STORAGE_BUCKET).remove([storage_path])

        logger.info(f"Image deleted successfully: {storage_path}")
        return True

    except Exception as exc:
        logger.error(f"Error deleting image from Supabase Storage: {exc}", exc_info=True)
        return False
