import inspect
import types
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from typeboard.fields import (
    AdminField,
    FieldInfo,
    extract_admin_field,
    get_enum_choices,
    infer_widget,
    label_from_name,
    unwrap_annotated,
)


def _is_depends(annotation: Any, default: Any) -> bool:
    """Detect FastAPI Depends() parameters."""
    if hasattr(annotation, "dependency") or hasattr(default, "dependency"):
        return True
    # Depends() inside Annotated metadata
    if get_origin(annotation) is Annotated:
        for arg in get_args(annotation)[1:]:
            if hasattr(arg, "dependency"):
                return True
    return False


def _is_optional(annotation: Any) -> bool:
    """Check if a type is X | None."""
    origin = get_origin(annotation)
    if origin is types.UnionType:
        args = get_args(annotation)
        return type(None) in args
    return False


def _build_field_info(
    name: str,
    annotation: Any,
    default: Any = inspect.Parameter.empty,
) -> FieldInfo:
    admin: AdminField | None = extract_admin_field(annotation)
    base_type = unwrap_annotated(annotation)
    optional = _is_optional(base_type)
    if optional:
        # Unwrap the Optional to get inner type
        non_none = [a for a in get_args(base_type) if a is not type(None)]
        base_type = non_none[0] if non_none else base_type

    has_default = default is not inspect.Parameter.empty
    required = not optional and not has_default

    # Auto-set widget for relationship fields
    if admin and admin.relationship and not admin.widget:
        origin = get_origin(base_type)
        widget = "multiselect" if origin is list else "select"
    else:
        widget = (admin.widget if admin and admin.widget else infer_widget(base_type))

    # Auto-set label from relationship resource name instead of field name
    if admin and admin.relationship and not admin.label:
        label = admin.relationship.replace("_", " ").title()
    else:
        label = (admin.label if admin and admin.label else label_from_name(name))

    return FieldInfo(
        name=name,
        python_type=base_type,
        widget=widget,
        label=label,
        read_only=admin.read_only if admin else False,
        hidden=admin.hidden if admin else False,
        required=required,
        default=default if has_default else None,
        filter=admin.filter if admin else None,
        column=admin.column if admin else True,
        order=admin.order if admin else None,
        enum_choices=get_enum_choices(base_type),
        choices_callable=admin.choices if admin else None,
        display_name=admin.display_name if admin else False,
        relationship=admin.relationship if admin else None,
        relationship_search=admin.relationship_search if admin else None,
    )


def extract_fields_from_model(model: type[BaseModel]) -> list[FieldInfo]:
    """Extract FieldInfo list from a Pydantic model."""
    hints = get_type_hints(model, include_extras=True)
    model_fields = model.model_fields
    result: list[FieldInfo] = []
    for field_name, model_field in model_fields.items():
        annotation = hints.get(field_name, str)
        default = model_field.default if model_field.default is not None else inspect.Parameter.empty
        if model_field.is_required():
            default = inspect.Parameter.empty
        result.append(_build_field_info(field_name, annotation, default))
    return result


def extract_fields_from_function(fn, skip_id: bool = False) -> list[FieldInfo]:
    """Extract FieldInfo list from a function's parameters."""
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)
    result: list[FieldInfo] = []

    for param_name, param in sig.parameters.items():
        if skip_id and param_name == "id":
            continue

        annotation = hints.get(param_name, param.annotation)
        default = param.default

        if _is_depends(annotation, default):
            continue

        base_type = unwrap_annotated(annotation)
        # Unwrap Optional for the BaseModel check
        check_type = base_type
        if _is_optional(check_type):
            non_none = [a for a in get_args(check_type) if a is not type(None)]
            if non_none:
                check_type = non_none[0]

        if isinstance(check_type, type) and issubclass(check_type, BaseModel):
            result.extend(extract_fields_from_model(check_type))
            continue

        result.append(_build_field_info(param_name, annotation, default))

    return result


def extract_return_type(fn) -> type | None:
    """Get the return type annotation of a function."""
    hints = get_type_hints(fn, include_extras=True)
    return hints.get("return")


def extract_page_item_type(return_type) -> type | None:
    """Extract T from Page[T]."""
    from typeboard.pagination import Page

    origin = get_origin(return_type)
    if origin is Page:
        args = get_args(return_type)
        return args[0] if args else None
    return None


def extract_columns(fn) -> list[FieldInfo]:
    """Extract column FieldInfo from a list function's Page[T] return type."""
    rt = extract_return_type(fn)
    if rt is None:
        return []
    item_type = extract_page_item_type(rt)
    if item_type is None:
        # Maybe it's a direct model
        if isinstance(rt, type) and issubclass(rt, BaseModel):
            return extract_fields_from_model(rt)
        return []
    if isinstance(item_type, type) and issubclass(item_type, BaseModel):
        return extract_fields_from_model(item_type)
    return []


@dataclass
class DependsParam:
    """A parameter that should be forwarded to FastAPI as a dependency."""
    name: str
    annotation: Any
    default: Any


def extract_depends_params(fn) -> list[DependsParam]:
    """Extract Depends() params from a function signature."""
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)
    result: list[DependsParam] = []
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        default = param.default
        if _is_depends(annotation, default):
            result.append(DependsParam(name=param_name, annotation=annotation, default=default))
    return result


def find_id_param(fn) -> str | None:
    """Find the ID parameter name. Resolution: AdminField(is_id=True) > 'id' > first non-DI param."""
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)

    # Pass 1: AdminField(is_id=True)
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        if _is_depends(annotation, param.default):
            continue
        admin = extract_admin_field(annotation)
        if admin and admin.is_id:
            return param_name

    # Pass 2: named 'id'
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        if _is_depends(annotation, param.default):
            continue
        if param_name == "id":
            return param_name

    # Pass 3: first non-DI param
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        if _is_depends(annotation, param.default):
            continue
        return param_name

    return None


def find_pagination_params(fn) -> tuple[str | None, str | None]:
    """Find page and page_size param names. Resolution: AdminField(pagination=...) > convention."""
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)
    page_param = None
    page_size_param = None

    # Pass 1: AdminField annotations
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        if _is_depends(annotation, param.default):
            continue
        admin = extract_admin_field(annotation)
        if admin and admin.pagination == "page":
            page_param = param_name
        elif admin and admin.pagination == "page_size":
            page_size_param = param_name

    # Pass 2: convention names
    if page_param is None and "page" in sig.parameters:
        ann = hints.get("page", sig.parameters["page"].annotation)
        if not _is_depends(ann, sig.parameters["page"].default):
            page_param = "page"
    if page_size_param is None and "page_size" in sig.parameters:
        ann = hints.get("page_size", sig.parameters["page_size"].annotation)
        if not _is_depends(ann, sig.parameters["page_size"].default):
            page_size_param = "page_size"

    return page_param, page_size_param


def find_sort_param(fn) -> str | None:
    """Find the sort param name. Resolution: AdminField(sort=True) > named 'sort'."""
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)

    # Pass 1: AdminField(sort=True)
    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, param.annotation)
        if _is_depends(annotation, param.default):
            continue
        admin = extract_admin_field(annotation)
        if admin and admin.sort:
            return param_name

    # Pass 2: named 'sort'
    if "sort" in sig.parameters:
        ann = hints.get("sort", sig.parameters["sort"].annotation)
        if not _is_depends(ann, sig.parameters["sort"].default):
            return "sort"

    return None
