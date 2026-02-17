import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Annotated, Any, get_args, get_origin
import types


@dataclass
class AdminField:
    label: str | None = None
    widget: str | None = None
    read_only: bool = False
    hidden: bool = False
    filter: str | None = None
    column: bool = True
    order: int | None = None
    is_id: bool = False
    pagination: str | None = None  # "page" or "page_size"
    sort: bool = False
    choices: Callable | None = None


@dataclass
class FieldInfo:
    """Resolved field metadata for rendering."""
    name: str
    python_type: type
    widget: str
    label: str
    read_only: bool = False
    hidden: bool = False
    required: bool = True
    default: Any = field(default=None)
    filter: str | None = None
    column: bool = True
    order: int | None = None
    enum_choices: list[tuple[str, str]] | None = None
    choices_callable: Callable | None = None


def _unwrap_optional(python_type: type) -> type:
    """Unwrap Optional/Union with None types, return the inner type."""
    origin = get_origin(python_type)
    args = get_args(python_type)
    if origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return python_type


def infer_widget(python_type: type) -> str:
    """Map a Python type to a default HTML widget."""
    python_type = _unwrap_optional(python_type)
    origin = get_origin(python_type)

    if isinstance(python_type, type) and issubclass(python_type, bool):
        return "checkbox"
    if isinstance(python_type, type) and issubclass(python_type, int):
        return "number"
    if isinstance(python_type, type) and issubclass(python_type, float):
        return "number"
    if isinstance(python_type, type) and issubclass(python_type, enum.Enum):
        return "select"
    if isinstance(python_type, type) and issubclass(python_type, datetime):
        return "datetime"
    if isinstance(python_type, type) and issubclass(python_type, date):
        return "date"
    if origin is list:
        return "multiselect"
    return "text"


def extract_admin_field(annotation: Any) -> AdminField | None:
    """Extract AdminField from an Annotated type, if present."""
    if get_origin(annotation) is Annotated:
        for arg in get_args(annotation)[1:]:
            if isinstance(arg, AdminField):
                return arg
    return None


def unwrap_annotated(annotation: Any) -> type:
    """Get the base type from Annotated[X, ...] -> X, or return as-is."""
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def get_enum_choices(python_type: type) -> list[tuple[str, str]] | None:
    """Extract (value, label) pairs from an Enum type."""
    python_type = _unwrap_optional(python_type)
    if isinstance(python_type, type) and issubclass(python_type, enum.Enum):
        return [(str(member.value), member.name.replace("_", " ").title()) for member in python_type]
    return None


def label_from_name(name: str) -> str:
    """Convert snake_case to Title Case."""
    return name.replace("_", " ").title()
