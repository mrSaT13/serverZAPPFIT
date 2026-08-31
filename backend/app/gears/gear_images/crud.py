"""CRUD for gear images."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import core.config as core_config
import core.decorators as core_decorators
import core.file_uploads as core_file_uploads
import core.logger as core_logger
import gears.gear.crud as gears_crud
import gears.gear_images.models as gear_images_models


@core_decorators.handle_db_errors
def get_gear_images(gear_id: int, token_user_id: int, db: Session) -> list[gear_images_models.GearImage]:
    gear = gears_crud.get_gear_user_by_id(token_user_id, gear_id, db)
    if not gear:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gear not found")
    stmt = select(gear_images_models.GearImage).where(gear_images_models.GearImage.gear_id == gear_id).order_by(gear_images_models.GearImage.created_at.desc())
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def create_gear_image(gear_id: int, image_path: str, db: Session) -> gear_images_models.GearImage:
    try:
        db_img = gear_images_models.GearImage(gear_id=gear_id, image_path=image_path)
        db.add(db_img)
        db.commit()
        db.refresh(db_img)
        return db_img
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate image path") from e


@core_decorators.handle_db_errors
def delete_gear_image(image_id: int, token_user_id: int, db: Session) -> None:
    stmt = select(gear_images_models.GearImage).where(gear_images_models.GearImage.id == image_id)
    img = db.scalars(stmt).first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gear image not found")
    gear = gears_crud.get_gear_user_by_id(token_user_id, img.gear_id, db)
    if not gear:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gear not found")
    if gear.user_id != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    path = img.image_path
    db.delete(img)
    db.commit()
    if path:
        try:
            core_file_uploads.safe_remove_within(path, base_dir=core_config.settings.GEAR_IMAGES_DIR)
        except HTTPException as err:
            core_logger.print_to_log(f"Refused to remove gear image outside dir id {image_id}: {err.detail}", "warning")
        except Exception:
            pass
