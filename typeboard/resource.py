from dataclasses import dataclass, field
from typing import Callable

from typeboard.fields import FieldInfo
from typeboard.introspection import (
    DependsParam,
    extract_columns,
    extract_depends_params,
    extract_fields_from_function,
    find_id_param,
)


@dataclass
class Resource:
    id: str
    label: str = ""
    list_fn: Callable | None = None
    get_fn: Callable | None = None
    create_fn: Callable | None = None
    update_fn: Callable | None = None
    delete_fn: Callable | None = None

    def __post_init__(self):
        if not self.label:
            self.label = self.id.replace("_", " ").title()

    # Cached introspection results (populated lazily)
    _columns: list[FieldInfo] | None = field(default=None, repr=False)
    _detail_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _create_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _update_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _filter_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _depends_cache: dict[str, list[DependsParam]] = field(default_factory=dict, repr=False)
    _id_param_name: str | None = field(default=None, repr=False, init=False)
    _id_param_resolved: bool = field(default=False, repr=False, init=False)

    @property
    def columns(self) -> list[FieldInfo]:
        if self._columns is None:
            fn = self.list_fn or self.get_fn
            self._columns = extract_columns(fn) if fn else []
        return self._columns

    @property
    def detail_fields(self) -> list[FieldInfo]:
        if self._detail_fields is None:
            fn = self.get_fn or self.list_fn
            self._detail_fields = extract_columns(fn) if fn else []
        return self._detail_fields

    @property
    def create_fields(self) -> list[FieldInfo]:
        if self._create_fields is None:
            self._create_fields = (
                extract_fields_from_function(self.create_fn, skip_id=True)
                if self.create_fn
                else []
            )
        return self._create_fields

    @property
    def update_fields(self) -> list[FieldInfo]:
        if self._update_fields is None:
            self._update_fields = (
                extract_fields_from_function(self.update_fn, skip_id=True)
                if self.update_fn
                else []
            )
        return self._update_fields

    @property
    def filter_fields(self) -> list[FieldInfo]:
        if self._filter_fields is None:
            if self.list_fn:
                all_fields = extract_fields_from_function(self.list_fn)
                self._filter_fields = [f for f in all_fields if f.filter]
            else:
                self._filter_fields = []
        return self._filter_fields

    def _fn_for_op(self, op: str) -> Callable | None:
        return getattr(self, f"{op}_fn", None)

    def get_depends_params(self, op: str) -> list[DependsParam]:
        if op not in self._depends_cache:
            fn = self._fn_for_op(op)
            self._depends_cache[op] = extract_depends_params(fn) if fn else []
        return self._depends_cache[op]

    @property
    def display_name_field(self) -> str:
        """Find the display name field for this resource.

        Priority: display_name=True > column named name/title/label > first non-ID string > "id".
        """
        for col in self.columns:
            if col.display_name:
                return col.name
        for col in self.columns:
            if col.name in ("name", "title", "label", "display_name"):
                return col.name
        for col in self.columns:
            if col.python_type is str and col.name not in ("id", "pk"):
                return col.name
        return "id"

    @property
    def id_param_name(self) -> str | None:
        if not self._id_param_resolved:
            for fn in (self.get_fn, self.update_fn, self.delete_fn):
                if fn is not None:
                    self._id_param_name = find_id_param(fn)
                    break
            self._id_param_resolved = True
        return self._id_param_name

    # Decorator-style registration
    @property
    def list(self):
        def decorator(fn):
            self.list_fn = fn
            return fn
        return decorator

    @property
    def get(self):
        def decorator(fn):
            self.get_fn = fn
            return fn
        return decorator

    @property
    def create(self):
        def decorator(fn):
            self.create_fn = fn
            return fn
        return decorator

    @property
    def update(self):
        def decorator(fn):
            self.update_fn = fn
            return fn
        return decorator

    @property
    def delete(self):
        def decorator(fn):
            self.delete_fn = fn
            return fn
        return decorator
