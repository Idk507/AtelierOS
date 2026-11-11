"""Normalize small studio images into metadata-free JPEG thumbnails."""

import base64
import binascii
import io

from PIL import Image, ImageOps

from packages.domain.design import DomainError


def thumbnail(encoded: str) -> str:
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 256_000:
            raise DomainError("image_too_large", 422)
        with Image.open(io.BytesIO(raw), formats=("JPEG",)) as source:
            if source.width * source.height > 4_000_000:
                raise DomainError("image_dimensions_too_large", 422)
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((320, 320))
            image.info.clear()
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=78)
    except (binascii.Error, ValueError, OSError, Image.DecompressionBombError) as exc:
        raise DomainError("invalid_reference_image", 422) from exc
    return base64.b64encode(output.getvalue()).decode("ascii")
