from fastapi.testclient import TestClient

from typeboard.pagination import Page
from typeboard.site import AdminSite


def my_list(page: int = 1, page_size: int = 25) -> Page[dict]:
    return Page(items=[], total=0, page=1, page_size=25)


def my_get(id: int) -> dict:
    return {"id": id}


def test_app_has_routes():
    site = AdminSite(title="Test")
    site.resource("items", list=my_list, get=my_get)
    app = site.as_asgi()
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append(route.path)
        elif hasattr(route, "routes"):
            for sub in route.routes:
                if hasattr(sub, "path"):
                    routes.append(sub.path)
    assert "/items/" in routes
    assert "/items/rows" in routes
    assert "/items/{id}" in routes


def test_no_create_route_when_no_create_fn():
    site = AdminSite(title="Test")
    site.resource("items", list=my_list)
    app = site.as_asgi()
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append(route.path)
        elif hasattr(route, "routes"):
            for sub in route.routes:
                if hasattr(sub, "path"):
                    routes.append(sub.path)
    assert "/items/new" not in routes


def test_index_returns_html():
    site = AdminSite(title="Test")
    site.resource("items", list=my_list)
    app = site.as_asgi()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Test" in resp.text
