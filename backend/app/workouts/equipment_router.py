"""Training-inventory endpoints (user's own dumbbells/barbells/machines).

Mounted under ``/workouts/equipment`` by ``workouts.router`` — routes are
registered before the ``/{plan_id}`` catch-alls.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.database as core_database
import workouts.equipment_crud as equipment_crud
import workouts.equipment_schema as equipment_schema

router = APIRouter()


@router.get("", response_model=list[equipment_schema.EquipmentRead])
async def list_equipment(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[equipment_schema.EquipmentRead]:
    """The authenticated user's training inventory."""
    rows = equipment_crud.list_equipment(token_user_id, db)
    return [equipment_schema.EquipmentRead.model_validate(r) for r in rows]


@router.post("", response_model=equipment_schema.EquipmentRead, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    payload: equipment_schema.EquipmentCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> equipment_schema.EquipmentRead:
    """Add an item (e.g. "Гантели 10 кг") to the inventory."""
    row = equipment_crud.create_equipment(token_user_id, payload, db)
    return equipment_schema.EquipmentRead.model_validate(row)


@router.put("/{item_id}", response_model=equipment_schema.EquipmentRead)
async def update_equipment(
    item_id: int,
    payload: equipment_schema.EquipmentUpdate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> equipment_schema.EquipmentRead:
    row = equipment_crud.update_equipment(token_user_id, item_id, payload, db)
    return equipment_schema.EquipmentRead.model_validate(row)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    item_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    equipment_crud.delete_equipment(token_user_id, item_id, db)
