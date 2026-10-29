"""CRUD for the user training inventory."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import core.decorators as core_decorators
import workouts.equipment_models as equipment_models
import workouts.equipment_schema as equipment_schema


@core_decorators.handle_db_errors
def list_equipment(user_id: int, db: Session) -> list[equipment_models.UserEquipment]:
    stmt = (
        select(equipment_models.UserEquipment)
        .where(equipment_models.UserEquipment.user_id == user_id)
        .order_by(equipment_models.UserEquipment.name)
    )
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def get_equipment(user_id: int, item_id: int, db: Session) -> equipment_models.UserEquipment:
    stmt = select(equipment_models.UserEquipment).where(
        equipment_models.UserEquipment.id == item_id,
        equipment_models.UserEquipment.user_id == user_id,
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return row


@core_decorators.handle_db_errors
def create_equipment(
    user_id: int, payload: equipment_schema.EquipmentCreate, db: Session
) -> equipment_models.UserEquipment:
    row = equipment_models.UserEquipment(user_id=user_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def update_equipment(
    user_id: int, item_id: int, payload: equipment_schema.EquipmentUpdate, db: Session
) -> equipment_models.UserEquipment:
    row = get_equipment(user_id, item_id, db)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def delete_equipment(user_id: int, item_id: int, db: Session) -> None:
    row = get_equipment(user_id, item_id, db)
    db.delete(row)
    db.commit()
