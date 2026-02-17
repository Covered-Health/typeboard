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
