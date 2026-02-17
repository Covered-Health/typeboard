from fastapi.testclient import TestClient
from pydantic import BaseModel

from typeboard.pagination import Page
from typeboard.site import AdminSite


class Item(BaseModel):
    id: int
    name: str


ITEMS = [Item(id=1, name="Alpha"), Item(id=2, name="Beta")]


def list_items(page: int = 1, page_size: int = 25) -> Page[Item]:
    return Page(items=ITEMS, total=len(ITEMS), page=page, page_size=page_size)


def get_item(id: int) -> Item:
    return next(i for i in ITEMS if i.id == id)


def test_list_page_renders():
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item)
    client = TestClient(site.as_asgi())
    resp = client.get("/items/")
    assert resp.status_code == 200
    assert "Items" in resp.text


def test_rows_returns_data():
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item)
    client = TestClient(site.as_asgi())
    resp = client.get("/items/rows")
    assert resp.status_code == 200
    assert "Alpha" in resp.text
    assert "Beta" in resp.text


def test_detail_page():
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item)
    client = TestClient(site.as_asgi())
    resp = client.get("/items/1")
    assert resp.status_code == 200
    assert "Alpha" in resp.text
