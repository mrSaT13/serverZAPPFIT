"""Router for gear images — upload / list / delete with carousel support."""

import uuid
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, UploadFile, status
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.config as core_config
import core.database as core_database
import core.file_uploads as core_file_uploads
import gears.gear.dependencies as gears_dependencies
import gears.gear_images.crud as gear_images_crud
import gears.gear_images.dependencies as gear_images_dependencies
import gears.gear_images.schema as gear_images_schema

router = APIRouter()

_ALLOWED_GEAR_IMAGE_EXTS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"})


def _safe_gear_filename(gear_id: int, original: str | None) -> str:
    base = PurePosixPath(original or "").name
    ext = PurePosixPath(base).suffix.lower()
    if ext not in _ALLOWED_GEAR_IMAGE_EXTS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")
    return f"{gear_id}_{uuid.uuid4().hex}{ext}"


def _to_read(img, request_host: str | None = None) -> gear_images_schema.GearImageRead:
    # image_path stored as absolute path; expose via static mount /gear_images/<filename>
    # For now return path as url suffix
    filename = PurePosixPath(img.image_path).name if img.image_path else ""
    url = f"/gear_images/{filename}" if filename else None
    return gear_images_schema.GearImageRead(
        id=img.id,
        gear_id=img.gear_id,
        image_path=img.image_path,
        created_at=img.created_at,
        image_url=url,
    )


@router.get(
    "/gear/{gear_id}",
    response_model=list[gear_images_schema.GearImageRead],
    status_code=status.HTTP_200_OK,
)
async def list_gear_images(
    gear_id: int,
    _validate_id: Annotated[Callable, Depends(gears_dependencies.validate_gear_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["gears:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[gear_images_schema.GearImageRead]:
    imgs = gear_images_crud.get_gear_images(gear_id, token_user_id, db)
    return [_to_read(i) for i in imgs]


@router.post(
    "/upload/gear/{gear_id}",
    response_model=gear_images_schema.GearImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_gear_image(
    file: UploadFile,
    gear_id: int,
    _validate_id: Annotated[Callable, Depends(gears_dependencies.validate_gear_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["gears:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> gear_images_schema.GearImageRead:
    # ownership check via crud
    gear_images_crud.get_gear_images(gear_id, token_user_id, db)
    filename = _safe_gear_filename(gear_id, file.filename)
    file_path = await core_file_uploads.save_validated_upload(
        file, kind=core_file_uploads.UploadKind.IMAGE, upload_dir=core_config.settings.GEAR_IMAGES_DIR, filename=filename
    )
    try:
        img = gear_images_crud.create_gear_image(gear_id, file_path, db)
        return _to_read(img)
    except HTTPException:
        await core_file_uploads.delete_files_by_pattern(core_config.settings.GEAR_IMAGES_DIR, filename)
        raise


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_gear_image(
    image_id: int,
    _validate_id: Annotated[Callable, Depends(gear_images_dependencies.validate_gear_image_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["gears:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    gear_images_crud.delete_gear_image(image_id, token_user_id, db)
