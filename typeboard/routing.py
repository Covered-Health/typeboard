import enum
import inspect
import mimetypes
from datetime import date, datetime
from pathlib import Path
from typing import Any, get_args, get_origin

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from typeboard.rendering import create_renderer
from typeboard.resource import Resource


def _coerce(value: Any, python_type: type) -> Any:
    """Coerce a form string value to the target Python type."""
    import types

    origin = get_origin(python_type)
    args = get_args(python_type)
    if origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            python_type = non_none[0]

    if value is None or value == "":
        return None
    if python_type is bool:
        return str(value).lower() in ("true", "1", "on", "yes")
    if python_type is int:
        return int(value)
    if python_type is float:
        return float(value)
    if isinstance(python_type, type) and issubclass(python_type, date) and not issubclass(python_type, datetime):
        return date.fromisoformat(str(value))
    if isinstance(python_type, type) and issubclass(python_type, datetime):
        return datetime.fromisoformat(str(value))
    if isinstance(python_type, type) and issubclass(python_type, enum.Enum):
        return python_type(value)
    return str(value)


def build_resource_router(resource: Resource, render) -> APIRouter:
    router = APIRouter(prefix=f"/{resource.name}", tags=[resource.name])

    if resource.list_fn:
        async def list_page(request: Request, _res=resource):
            return render("list.html", resource=_res, request=request)

        async def rows(request: Request, _res=resource):
            from typeboard.pagination import Page

            page = int(request.query_params.get("page", "1"))
            page_size = int(request.query_params.get("page_size", "25"))
            sort = request.query_params.get("sort")

            kwargs: dict[str, Any] = {"page": page, "page_size": page_size}
            if sort:
                kwargs["sort"] = sort
            for ff in _res.filter_fields:
                val = request.query_params.get(ff.name)
                if val:
                    kwargs[ff.name] = val

            # Only pass kwargs the function actually accepts
            sig = inspect.signature(_res.list_fn)
            valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            result = _res.list_fn(**valid_kwargs)

            items = []
            page_info = None
            if isinstance(result, Page):
                items = result.items
                page_info = result
            elif isinstance(result, list):
                items = result

            return render(
                "_table_rows.html",
                resource=_res,
                request=request,
                items=items,
                page_info=page_info,
                columns=_res.columns,
            )

        router.add_api_route("/", list_page, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/rows", rows, methods=["GET"], response_class=HTMLResponse)

    if resource.get_fn:
        async def detail_page(request: Request, id: str, _res=resource):
            coerced_id = _coerce_id(id, _res.get_fn)
            item = _res.get_fn(coerced_id)
            columns = _res.columns
            return render("detail.html", resource=_res, request=request, id=id, item=item, columns=columns)

        router.add_api_route("/{id}", detail_page, methods=["GET"], response_class=HTMLResponse)

    if resource.create_fn:
        async def create_form(request: Request, _res=resource):
            fields = _res.create_fields
            return render("form.html", resource=_res, request=request, mode="create", fields=fields, values={}, errors=[])

        async def create_submit(request: Request, _res=resource):
            from pydantic import BaseModel
            fields = _res.create_fields
            form_data = await request.form()
            values = {}
            for field in fields:
                if field.hidden or field.read_only:
                    continue
                raw = form_data.get(field.name)
                if raw is None or raw == "":
                    if not field.required:
                        values[field.name] = field.default
                    continue
                values[field.name] = _coerce(raw, field.python_type)

            # Call create function
            sig = inspect.signature(_res.create_fn)
            params = list(sig.parameters.values())
            # Check if function takes a single Pydantic model param
            model_param = None
            for p in params:
                hints = inspect.get_annotations(_res.create_fn, eval_str=True)
                ann = hints.get(p.name)
                if ann and isinstance(ann, type) and issubclass(ann, BaseModel):
                    model_param = (p.name, ann)
                    break

            if model_param:
                name, model_cls = model_param
                model_instance = model_cls(**values)
                result = _res.create_fn(**{name: model_instance})
            else:
                result = _res.create_fn(**values)

            # Redirect to detail or list
            if _res.get_fn and result is not None:
                item_id_val = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None)
                if item_id_val is not None:
                    return RedirectResponse(
                        url=f"{request.scope.get('root_path', '')}/{_res.name}/{item_id_val}",
                        status_code=303,
                    )
            return RedirectResponse(
                url=f"{request.scope.get('root_path', '')}/{_res.name}/",
                status_code=303,
            )

        router.add_api_route("/new", create_form, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/new", create_submit, methods=["POST"])

    if resource.update_fn:
        async def edit_form(request: Request, id: str, _res=resource):
            item = _res.get_fn(int(id)) if _res.get_fn else None
            fields = _res.update_fields
            values = {}
            if item:
                for f in fields:
                    if isinstance(item, dict):
                        values[f.name] = item.get(f.name, f.default)
                    else:
                        values[f.name] = getattr(item, f.name, f.default)
            return render("form.html", resource=_res, request=request, mode="edit", id=id, fields=fields, values=values, errors=[])

        async def edit_submit(request: Request, id: str, _res=resource):
            from pydantic import BaseModel
            fields = _res.update_fields
            form_data = await request.form()
            values = {}
            for field in fields:
                if field.hidden or field.read_only:
                    continue
                raw = form_data.get(field.name)
                if raw is None or raw == "":
                    if not field.required:
                        values[field.name] = field.default
                    continue
                values[field.name] = _coerce(raw, field.python_type)

            coerced_id = _coerce_id(id, _res.update_fn)

            sig = inspect.signature(_res.update_fn)
            params = list(sig.parameters.values())
            model_param = None
            for p in params:
                hints = inspect.get_annotations(_res.update_fn, eval_str=True)
                ann = hints.get(p.name)
                if ann and isinstance(ann, type) and issubclass(ann, BaseModel):
                    model_param = (p.name, ann)
                    break

            if model_param:
                name, model_cls = model_param
                model_instance = model_cls(**values)
                _res.update_fn(coerced_id, **{name: model_instance})
            else:
                _res.update_fn(coerced_id, **values)

            return RedirectResponse(
                url=f"{request.scope.get('root_path', '')}/{_res.name}/{id}",
                status_code=303,
            )

        router.add_api_route("/{id}/edit", edit_form, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/{id}/edit", edit_submit, methods=["POST"])

    if resource.delete_fn:
        async def delete_item(request: Request, id: str, _res=resource):
            coerced_id = _coerce_id(id, _res.delete_fn)
            _res.delete_fn(coerced_id)
            return HTMLResponse(content="", headers={"HX-Redirect": f"{request.scope.get('root_path', '')}/{_res.name}/"})

        router.add_api_route("/{id}", delete_item, methods=["DELETE"])

    return router


def _coerce_id(id_str: str, fn) -> Any:
    """Coerce the ID string to match the function's first non-DI parameter type."""
    if fn is None:
        return id_str
    sig = inspect.signature(fn)
    hints = inspect.get_annotations(fn, eval_str=True)
    for name, param in sig.parameters.items():
        if name == "id" or name == list(sig.parameters.keys())[0]:
            ann = hints.get(name, str)
            return _coerce(id_str, ann)
    return id_str


def build_app(site) -> FastAPI:
    admin_app = FastAPI(title=site.title, docs_url=None, redoc_url=None)

    # If logo_url is a Path, serve it as a static file and replace with the URL
    if isinstance(site.logo_url, Path):
        logo_path = site.logo_url.resolve()
        media_type = (
            mimetypes.guess_type(str(logo_path))[0]
            or "application/octet-stream"
        )

        async def serve_logo():
            return FileResponse(logo_path, media_type=media_type)

        admin_app.add_api_route("/_static/logo{ext}", serve_logo, methods=["GET"])
        site.logo_url = f"/_static/logo{logo_path.suffix}"

    render = create_renderer(site)

    dependencies = []
    if site.auth_dependency:
        dependencies.append(Depends(site.auth_dependency))

    main_router = APIRouter(dependencies=dependencies)

    async def index(request: Request):
        return render("index.html", request=request)

    main_router.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse)

    for resource in site.resources.values():
        resource_router = build_resource_router(resource, render)
        main_router.include_router(resource_router)

    admin_app.include_router(main_router)
    return admin_app
