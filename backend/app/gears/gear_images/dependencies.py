"""Validators for gear images."""

from fastapi import HTTPException, status

import core.dependencies as core_dependencies


def validate_gear_image_id(image_id: int) -> None:
    core_dependencies.validate_id(identifier=image_id, min_value=0, message="Invalid gear image ID")
