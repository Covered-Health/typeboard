from dataclasses import dataclass, field
from typing import Callable

from typeboard.fields import FieldInfo
from typeboard.introspection import extract_columns, extract_fields_from_function


@dataclass
class Resource:
    name: str
    list_fn: Callable | None = None
    get_fn: Callable | None = None
    create_fn: Callable | None = None
    update_fn: Callable | None = None
    delete_fn: Callable | None = None

    # Cached introspection results (populated lazily)
    _columns: list[FieldInfo] | None = field(default=None, repr=False)
    _create_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _update_fields: list[FieldInfo] | None = field(default=None, repr=False)
    _filter_fields: list[FieldInfo] | None = field(default=None, repr=False)

    @property
    def columns(self) -> list[FieldInfo]:
        if self._columns is None:
            fn = self.list_fn or self.get_fn
            self._columns = extract_columns(fn) if fn else []
        return self._columns

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
