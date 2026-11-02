import io

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError


class VisionDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clothing: str = Field(default="", max_length=1000)
    marks: str = Field(default="", max_length=1000)
    scene: str = Field(default="", max_length=1000)


def sanitize_photo(data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 20_000_000:
                raise AppError("invalid_photo", "Photo must be at most 20 megapixels.", 422)
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise AppError("invalid_photo", "Please use a JPEG, PNG or WebP photo.", 422)
            clean = ImageOps.exif_transpose(image).convert("RGB")
            clean.thumbnail((2048, 2048))
            output = io.BytesIO()
            clean.save(output, format="JPEG", quality=85)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AppError("invalid_photo", "This photo could not be read.", 422) from exc
