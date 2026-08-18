from typing import Any
from unittest.mock import MagicMock


def mock_model(model_class: type, **attrs: Any) -> MagicMock:
    instance = MagicMock(spec=model_class)
    for key, value in attrs.items():
        setattr(instance, key, value)
    return instance
