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


from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, ConfigDict

from typeboard.fields import AdminField


# Simulate a dependency (like get_db)
def fake_db_dep():
    yield "fake_db_session"


FakeDB = Annotated[str, Depends(fake_db_dep)]


class OrgRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


def list_orgs_with_dep(
    db: FakeDB,
    page: int = 1,
    page_size: int = 25,
) -> Page[OrgRead]:
    assert db == "fake_db_session"
    return Page(items=[OrgRead(id=1, name="Acme")], total=1, page=page, page_size=page_size)


def get_org_with_dep(
    db: FakeDB,
    org_id: Annotated[int, AdminField(is_id=True)],
) -> OrgRead:
    assert db == "fake_db_session"
    return OrgRead(id=org_id, name="Acme")


def test_list_with_depends():
    site = AdminSite(title="Test")
    site.resource("orgs", list=list_orgs_with_dep, get=get_org_with_dep)
    client = TestClient(site.as_asgi())
    resp = client.get("/orgs/rows")
    assert resp.status_code == 200
    assert "Acme" in resp.text


def test_get_with_depends_and_custom_id():
    site = AdminSite(title="Test")
    site.resource("orgs", list=list_orgs_with_dep, get=get_org_with_dep)
    client = TestClient(site.as_asgi())
    resp = client.get("/orgs/42")
    assert resp.status_code == 200
    assert "Acme" in resp.text
