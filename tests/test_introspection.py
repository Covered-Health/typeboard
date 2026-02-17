from typing import Annotated

from pydantic import BaseModel

from typeboard.fields import AdminField
from typeboard.introspection import (
    extract_columns,
    extract_fields_from_function,
    extract_fields_from_model,
    extract_page_item_type,
    extract_return_type,
)
from typeboard.pagination import Page


class ItemSchema(BaseModel):
    id: int
    name: str
    description: Annotated[str | None, AdminField(widget="textarea")] = None


class CreateSchema(BaseModel):
    name: str
    description: Annotated[str | None, AdminField(widget="textarea")] = None


def sample_list(
    page: int = 1,
    name: Annotated[str | None, AdminField(filter="search")] = None,
) -> Page[ItemSchema]:
    ...


def sample_get(id: int) -> ItemSchema:
    ...


def sample_create(data: CreateSchema) -> ItemSchema:
    ...


def sample_create_plain(
    name: str,
    description: Annotated[str | None, AdminField(widget="textarea")] = None,
) -> ItemSchema:
    ...


def test_extract_fields_from_model():
    fields = extract_fields_from_model(CreateSchema)
    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[0].widget == "text"
    assert fields[1].name == "description"
    assert fields[1].widget == "textarea"


def test_extract_fields_from_function_with_model():
    fields = extract_fields_from_function(sample_create)
    assert len(fields) == 2
    assert fields[0].name == "name"


def test_extract_fields_from_function_plain_params():
    fields = extract_fields_from_function(sample_create_plain)
    assert len(fields) == 2
    assert fields[0].name == "name"
    assert fields[1].widget == "textarea"


def test_extract_filter_fields():
    fields = extract_fields_from_function(sample_list)
    filters = [f for f in fields if f.filter]
    assert len(filters) == 1
    assert filters[0].name == "name"
    assert filters[0].filter == "search"


def test_extract_return_type():
    rt = extract_return_type(sample_list)
    assert rt is not None


def test_extract_page_item_type():
    rt = extract_return_type(sample_list)
    item_type = extract_page_item_type(rt)
    assert item_type is ItemSchema


def test_extract_columns():
    cols = extract_columns(sample_list)
    assert len(cols) == 3
    assert cols[0].name == "id"


def test_skips_id_for_create():
    def create_with_id(id: int, name: str) -> ItemSchema:
        ...
    fields = extract_fields_from_function(create_with_id, skip_id=True)
    names = [f.name for f in fields]
    assert "id" not in names
    assert "name" in names


from fastapi import Depends
from typeboard.introspection import (
    extract_depends_params,
    find_id_param,
    find_pagination_params,
    find_sort_param,
)


def fake_dep():
    yield "fake_db"


def fn_with_depends(
    db: Annotated[str, Depends(fake_dep)],
    name: str,
) -> str:
    ...


def fn_with_id_convention(id: int, name: str) -> str:
    ...


def fn_with_id_annotation(
    iam_org_id: Annotated[str, AdminField(is_id=True)],
    name: str,
) -> str:
    ...


def fn_with_id_fallback(
    db: Annotated[str, Depends(fake_dep)],
    org_id: int,
) -> str:
    ...


def fn_with_pagination(
    page: int = 1,
    page_size: int = 25,
    name: str | None = None,
) -> str:
    ...


def fn_with_sort(sort: str | None = None) -> str:
    ...


def fn_with_annotated_sort(
    order_by: Annotated[str | None, AdminField(sort=True)] = None,
) -> str:
    ...


def test_extract_depends_params():
    deps = extract_depends_params(fn_with_depends)
    assert len(deps) == 1
    assert deps[0].name == "db"


def test_extract_depends_skipped_in_fields():
    fields = extract_fields_from_function(fn_with_depends)
    names = [f.name for f in fields]
    assert "db" not in names
    assert "name" in names


def test_find_id_param_convention():
    assert find_id_param(fn_with_id_convention) == "id"


def test_find_id_param_annotation():
    assert find_id_param(fn_with_id_annotation) == "iam_org_id"


def test_find_id_param_fallback():
    assert find_id_param(fn_with_id_fallback) == "org_id"


def test_find_pagination_params():
    page_param, page_size_param = find_pagination_params(fn_with_pagination)
    assert page_param == "page"
    assert page_size_param == "page_size"


def test_find_sort_param_convention():
    assert find_sort_param(fn_with_sort) == "sort"


def test_find_sort_param_annotation():
    assert find_sort_param(fn_with_annotated_sort) == "order_by"
