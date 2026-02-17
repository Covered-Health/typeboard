from fastapi.testclient import TestClient
from pydantic import BaseModel

from typeboard.pagination import Page
from typeboard.site import AdminSite


class Item(BaseModel):
    id: int
    name: str


ITEMS: list[Item] = []
NEXT_ID = 1


def list_items(page: int = 1, page_size: int = 25) -> Page[Item]:
    return Page(items=list(ITEMS), total=len(ITEMS), page=page, page_size=page_size)


def get_item(id: int) -> Item:
    return next(i for i in ITEMS if i.id == id)


def create_item(name: str) -> Item:
    global NEXT_ID
    item = Item(id=NEXT_ID, name=name)
    ITEMS.append(item)
    NEXT_ID += 1
    return item


def update_item(id: int, name: str) -> Item:
    for i, item in enumerate(ITEMS):
        if item.id == id:
            ITEMS[i] = Item(id=id, name=name)
            return ITEMS[i]
    raise ValueError(f"Item {id} not found")


def delete_item(id: int) -> None:
    global ITEMS
    ITEMS[:] = [i for i in ITEMS if i.id != id]


def setup_function():
    global ITEMS, NEXT_ID
    ITEMS.clear()
    NEXT_ID = 1


def test_create_form_renders():
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, create=create_item)
    client = TestClient(site.as_asgi())
    resp = client.get("/items/new")
    assert resp.status_code == 200
    assert "name" in resp.text.lower()


def test_create_submit():
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item, create=create_item)
    client = TestClient(site.as_asgi())
    resp = client.post("/items/new", data={"name": "Test Item"}, follow_redirects=False)
    assert resp.status_code in (200, 302, 303)
    assert len(ITEMS) == 1
    assert ITEMS[0].name == "Test Item"


def test_delete():
    ITEMS.append(Item(id=1, name="To Delete"))
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, delete=delete_item)
    client = TestClient(site.as_asgi())
    resp = client.delete("/items/1")
    assert resp.status_code == 200
    assert len(ITEMS) == 0


def test_edit_form_renders():
    ITEMS.append(Item(id=1, name="Original"))
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item, update=update_item)
    client = TestClient(site.as_asgi())
    resp = client.get("/items/1/edit")
    assert resp.status_code == 200
    assert "Original" in resp.text


def test_edit_submit():
    ITEMS.append(Item(id=1, name="Original"))
    site = AdminSite(title="Test")
    site.resource("items", list=list_items, get=get_item, update=update_item)
    client = TestClient(site.as_asgi())
    resp = client.post("/items/1/edit", data={"name": "Updated"}, follow_redirects=False)
    assert resp.status_code in (200, 302, 303)
    assert ITEMS[0].name == "Updated"
