from typing import Annotated

from fastapi import Depends

from typeboard.fields import AdminField
from typeboard.pagination import Page
from typeboard.site import AdminSite


def my_list(page: int = 1) -> Page[dict]:
    return Page(items=[], total=0, page=1, page_size=25)


def my_get(id: int) -> dict:
    return {}


def test_resource_kwargs():
    site = AdminSite(title="Test")
    site.resource("items", list=my_list, get=my_get)
    assert "items" in site.resources
    assert site.resources["items"].list_fn is my_list
    assert site.resources["items"].get_fn is my_get


def test_resource_decorator():
    site = AdminSite(title="Test")
    items = site.resource("items")

    @items.list
    def list_items(page: int = 1) -> Page[dict]:
        return Page(items=[], total=0, page=1, page_size=25)

    assert site.resources["items"].list_fn is list_items


def test_graceful_degradation():
    site = AdminSite(title="Test")
    site.resource("items", list=my_list)
    res = site.resources["items"]
    assert res.get_fn is None
    assert res.create_fn is None
    assert res.update_fn is None
    assert res.delete_fn is None


def fake_dep():
    yield "db"


def list_with_db(
    db: Annotated[str, Depends(fake_dep)],
    page: int = 1,
    page_size: int = 25,
) -> dict:
    return {}


def get_with_db(
    db: Annotated[str, Depends(fake_dep)],
    org_id: Annotated[int, AdminField(is_id=True)],
) -> dict:
    return {"id": org_id}


def test_resource_stores_depends_params():
    site = AdminSite(title="Test")
    res = site.resource("orgs", list=list_with_db, get=get_with_db)
    list_deps = res.get_depends_params("list")
    assert len(list_deps) == 1
    assert list_deps[0].name == "db"


def test_resource_resolves_id_param():
    site = AdminSite(title="Test")
    res = site.resource("orgs", get=get_with_db)
    assert res.id_param_name == "org_id"
