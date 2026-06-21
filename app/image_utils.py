import uuid  # For generating unique file name
from io import BytesIO # Working with image bytes in memory
from pathlib import Path # For file operations

from PIL import Image, ImageOps

from config import settings
import boto3 
from starlette.concurrency import run_in_threadpool

# Pillow is a CPUBound Task and it will block the event loop in async condition
# So we need to write our functions here as synchronus functions and run using thread 

# PROFILE_PICS_DIR = Path("media/profile_pics")


## _get_s3_client helper for image_utils.py
def _get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=(
            settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None
        ),
        aws_secret_access_key=(
            settings.s3_secret_access_key.get_secret_value()
            if settings.s3_secret_access_key
            else None
        ),
        endpoint_url=settings.s3_endpoint_url,
    )

## Process Image Function
# def process_profile_image(content: bytes) -> str:
#     with Image.open(BytesIO(content)) as original:
#         img = ImageOps.exif_transpose(original) # fix orentation issue

#         img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS) # crop to 300x300 pixels

#         if img.mode in ("RGBA", "LA", "P"):
#             img = img.convert("RGB")

#         filename = f"{uuid.uuid4().hex}.jpg"
#         filepath = PROFILE_PICS_DIR / filename

#         PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)

#         img.save(filepath, "JPEG", quality=85, optimize=True)

#     return filename


def process_profile_image(content: bytes) -> tuple[bytes, str]:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original) # fix orentation issue

        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS) # crop to 300x300 pixels

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"
        output = BytesIO()
        
        img.save(output, "JPEG", quality=85, optimize=True)
        output.seek(0)

    return output.read(), filename


## Delete Profile Image Function
# def delete_profile_image(filename: str | None) -> None:
#     if filename is None:
#         return

#     filepath = PROFILE_PICS_DIR / filename
#     if filepath.exists():
#         filepath.unlink() # deletion

## _upload_to_s3 and _delete_from_s3 for image_utils.py
def _upload_to_s3(file_bytes: bytes, key: str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )


def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)


## Async S3 wrappers for image_utils.py
async def upload_profile_image(file_bytes: bytes, filename: str) -> None:
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_upload_to_s3, file_bytes, key)


async def delete_profile_image(filename: str | None) -> None:
    if filename is None:
        return
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_delete_from_s3, key)


