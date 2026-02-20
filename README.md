# Typeboard

Type-introspecting admin dashboard framework for FastAPI.

Typeboard generates a full admin UI (list, detail, create, update, delete) by introspecting the type annotations on your FastAPI endpoint functions — no model registration or schema duplication required.

## Features

- **Zero-config introspection** — reads Python type hints, `Annotated` metadata, and Pydantic models to build forms, tables, and filters automatically
- **CRUD out of the box** — register `list`, `get`, `create`, `update`, and `delete` callables per resource
- **Pagination** — generic `Page[T]` type with server-side pagination support
- **Filtering & sorting** — declare filterable/sortable fields with `AdminField` annotations
- **Relationship linking** — chips that link to related resource detail pages, with search support
- **Sidebar sections** — group resources under named headings
- **Theming** — built-in light/dark themes via Bootstrap 5.3
- **Auth** — optional `auth_dependency` on `AdminSite` to protect all admin routes
- **Decorator API** — register endpoints with `@resource.list`, `@resource.get`, etc.

## Installation

```bash
pip install typeboard
```

Requires Python ~=3.12 and FastAPI >=0.100.

## Quick Start

```python
from typing import Annotated
from fastapi import FastAPI
from typeboard import AdminSite, AdminField, Page

app = FastAPI()

# 1. Create an admin site
admin = AdminSite(title="My Admin")

# 2. Register a resource
users = admin.resource("users", label="Users")

@users.list
async def list_users(
    page: Annotated[int, AdminField(pagination="page")] = 1,
    page_size: Annotated[int, AdminField(pagination="page_size")] = 25,
) -> Page[UserSchema]:
    ...

@users.get
async def get_user(id: int) -> UserSchema:
    ...

# 3. Mount the admin as a sub-application
app.mount("/admin", admin.as_asgi())
```

## Core Concepts

### AdminSite

The top-level object that holds resources and builds the ASGI app.

```python
admin = AdminSite(
    title="My Admin",
    logo_url="/static/logo.png",
    auth_dependency=require_admin_role,
    theme=DARK,
)
```

### Resource

Represents a single entity in the admin (e.g. users, orders). Register CRUD functions directly or via decorators:

```python
# Direct registration
admin.resource("orders", list=list_orders, get=get_order, create=create_order)

# Decorator style
orders = admin.resource("orders")

@orders.list
async def list_orders(...) -> Page[OrderSchema]:
    ...
```

### AdminField

Controls how fields are rendered in the admin UI. Applied via `Annotated`:

```python
from typing import Annotated
from typeboard import AdminField

class UserSchema(BaseModel):
    id: int
    name: Annotated[str, AdminField(display_name=True)]
    email: str
    role: Annotated[Role, AdminField(filter="select")]
    created_at: Annotated[datetime, AdminField(read_only=True)]
    org_id: Annotated[int, AdminField(relationship="organizations")]
```

### Page

Generic pagination wrapper. Return `Page[T]` from list endpoints:

```python
from typeboard import Page

Page(items=[...], total=100, page=1, page_size=25)
```

### Sidebar Sections

Group resources under headings:

```python
admin.section("Users & Auth")
admin.resource("users", ...)
admin.resource("roles", ...)

admin.section("Content")
admin.resource("articles", ...)
```

## Development

```bash
uv sync
uv run pytest
```

## License

Proprietary.
