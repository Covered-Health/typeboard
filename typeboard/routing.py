import enum
import inspect
import mimetypes
from datetime import date, datetime
from pathlib import Path
from typing import Any, get_args, get_origin

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from typeboard.fields import FieldInfo, unwrap_annotated
from typeboard.introspection import (
    DependsParam,
    extract_depends_params,
    find_pagination_params,
    find_sort_param,
)
from typeboard.rendering import create_renderer
from typeboard.resource import Resource


def _coerce(value: Any, python_type: type) -> Any:
    """Coerce a form string value to the target Python type."""
    import types as _types

    origin = get_origin(python_type)
    args = get_args(python_type)
    if origin is _types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            python_type = non_none[0]

    if origin is list:
        inner_type = args[0] if args else str
        if isinstance(value, list):
            return [_coerce(v, inner_type) for v in value]
        if value is None or value == "":
            return []
        return [_coerce(value, inner_type)]

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


def _coerce_id(id_str: str, fn, id_param_name: str | None = None) -> Any:
    """Coerce the ID string to match the function's ID parameter type."""
    if fn is None:
        return id_str
    target_name = id_param_name or "id"
    hints = inspect.get_annotations(fn, eval_str=True)
    ann = hints.get(target_name, str)
    base = unwrap_annotated(ann)
    return _coerce(id_str, base)


def _inject_depends(handler, depends_params: list[DependsParam]):
    """Add DI params to a handler's __signature__ so FastAPI resolves them.

    Always strips **kwargs from the signature (FastAPI can't handle VAR_KEYWORD),
    then appends explicit keyword-only parameters for each DI dependency.
    """
    sig = inspect.signature(handler)
    existing_params = list(sig.parameters.values())

    # Remove **kwargs from existing params (FastAPI doesn't support VAR_KEYWORD)
    filtered = [p for p in existing_params if p.kind != inspect.Parameter.VAR_KEYWORD]

    for dp in depends_params:
        filtered.append(
            inspect.Parameter(
                dp.name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=dp.default if dp.default is not inspect.Parameter.empty else inspect.Parameter.empty,
                annotation=dp.annotation,
            )
        )

    handler.__signature__ = sig.replace(parameters=filtered)
    return handler


def _resolve_choices(fields: list[FieldInfo], di_kwargs: dict[str, Any]) -> None:
    """Call choices callables to populate enum_choices for multiselect fields."""
    for f in fields:
        if f.choices_callable:
            sig = inspect.signature(f.choices_callable)
            call_kwargs = {k: v for k, v in di_kwargs.items() if k in sig.parameters}
            f.enum_choices = f.choices_callable(**call_kwargs)


def _collect_choices_deps(fields: list[FieldInfo]) -> list[DependsParam]:
    """Extract DI params needed by choices callables."""
    seen: set[str] = set()
    result: list[DependsParam] = []
    for f in fields:
        if f.choices_callable:
            for dp in extract_depends_params(f.choices_callable):
                if dp.name not in seen:
                    seen.add(dp.name)
                    result.append(dp)
    return result


# ---------------------------------------------------------------------------
# Relationship helpers
# ---------------------------------------------------------------------------

def _find_search_param(target_resource: Resource, field: FieldInfo) -> str | None:
    """Find the filter param on the target's list_fn to use for search.

    Priority: field.relationship_search override > param matching display_name_field
    > first filter="search" param.
    """
    if field.relationship_search:
        return field.relationship_search
    display = target_resource.display_name_field
    for ff in target_resource.filter_fields:
        if ff.name == display:
            return ff.name
    for ff in target_resource.filter_fields:
        if ff.filter == "search":
            return ff.name
    return None


def _setup_relationships(fields: list[FieldInfo], site) -> None:
    """For relationship fields, auto-generate choices callables from the target resource."""
    if site is None:
        return
    for f in fields:
        if not f.relationship or f.choices_callable:
            continue
        target = site.resources.get(f.relationship)
        if not target or not target.list_fn:
            continue
        display = target.display_name_field
        f.choices_callable = _build_relationship_choices(target, display)


def _build_relationship_choices(target_resource: Resource, display_field: str):
    """Create a choices callable that fetches items from the target resource."""
    from typeboard.pagination import Page

    list_fn = target_resource.list_fn

    def choices_fn(**kwargs):
        sig = inspect.signature(list_fn)
        call_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
        # Use a reasonable page size to get items for the initial load
        page_param, ps_param = find_pagination_params(list_fn)
        if ps_param:
            call_kwargs[ps_param] = 200
        if page_param:
            call_kwargs[page_param] = 1
        result = list_fn(**call_kwargs)
        items = result.items if isinstance(result, Page) else (result if isinstance(result, list) else [])
        out = []
        for item in items:
            item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            item_label = item.get(display_field) if isinstance(item, dict) else getattr(item, display_field, None)
            out.append((str(item_id), str(item_label)))
        return out

    # Copy DI signature from target's list_fn so _collect_choices_deps works
    di_params = extract_depends_params(list_fn)
    params = []
    for dp in di_params:
        params.append(
            inspect.Parameter(
                dp.name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=dp.default if dp.default is not inspect.Parameter.empty else inspect.Parameter.empty,
                annotation=dp.annotation,
            )
        )
    if params:
        choices_fn.__signature__ = inspect.Signature(parameters=params)

    return choices_fn


def _collect_relationship_deps(fields: list[FieldInfo], site) -> list[DependsParam]:
    """Extract DI params needed by relationship target list_fns."""
    if site is None:
        return []
    seen: set[str] = set()
    result: list[DependsParam] = []
    for f in fields:
        if not f.relationship:
            continue
        target = site.resources.get(f.relationship)
        if not target or not target.list_fn:
            continue
        for dp in extract_depends_params(target.list_fn):
            if dp.name not in seen:
                seen.add(dp.name)
                result.append(dp)
    return result


def _resolve_detail_relationships(item, fields: list[FieldInfo], site, di_kwargs: dict) -> Any:
    """Replace relationship ID fields with display names for the detail view."""
    from typeboard.pagination import Page

    modifications = {}
    for f in fields:
        if not f.relationship:
            continue
        target = site.resources.get(f.relationship)
        if not target or not target.list_fn:
            continue

        # Get current IDs from item
        ids = item.get(f.name) if isinstance(item, dict) else getattr(item, f.name, None)
        if ids is None:
            continue

        display = target.display_name_field

        # Fetch items from target resource
        sig = inspect.signature(target.list_fn)
        call_kwargs = {k: v for k, v in di_kwargs.items() if k in sig.parameters}
        page_param, ps_param = find_pagination_params(target.list_fn)
        if ps_param:
            call_kwargs[ps_param] = 10000
        if page_param:
            call_kwargs[page_param] = 1
        result = target.list_fn(**call_kwargs)
        items = result.items if isinstance(result, Page) else (result if isinstance(result, list) else [])

        # Build ID → display name map
        id_map = {}
        for t in items:
            t_id = t.get("id") if isinstance(t, dict) else getattr(t, "id", None)
            t_label = t.get(display) if isinstance(t, dict) else getattr(t, display, None)
            id_map[t_id] = str(t_label)

        # Replace IDs with names
        if isinstance(ids, list):
            modifications[f.name] = [id_map.get(i, str(i)) for i in ids]
        else:
            modifications[f.name] = id_map.get(ids, str(ids))

    if not modifications:
        return item

    # Create a dict copy with modifications
    if isinstance(item, dict):
        return {**item, **modifications}
    if hasattr(item, "model_dump"):
        data = item.model_dump()
        data.update(modifications)
        return data
    import copy
    new_item = copy.copy(item)
    for k, v in modifications.items():
        setattr(new_item, k, v)
    return new_item


def _register_options_endpoints(router: APIRouter, resource: Resource, site, render) -> None:
    """Register GET /options/{field_name} for each relationship field."""
    from typeboard.pagination import Page

    # Collect all relationship fields across update, create, and detail
    seen_fields: set[str] = set()
    all_fields: list[FieldInfo] = []
    for field_list in (resource.update_fields, resource.create_fields, resource.detail_fields):
        for f in field_list:
            if f.relationship and f.name not in seen_fields:
                seen_fields.add(f.name)
                all_fields.append(f)

    for rel_field in all_fields:
        target = site.resources.get(rel_field.relationship)
        if not target or not target.list_fn:
            continue

        target_list_fn = target.list_fn
        display = target.display_name_field
        search_param = _find_search_param(target, rel_field)
        target_deps = extract_depends_params(target_list_fn)

        async def options_handler(
            request: Request,
            _target=target,
            _list_fn=target_list_fn,
            _display=display,
            _search_param=search_param,
            _target_deps=target_deps,
            **kwargs,
        ):
            q = request.query_params.get("q", "").strip()
            selected_raw = request.query_params.get("selected", "")
            selected_ids = [s.strip() for s in selected_raw.split(",") if s.strip()]

            sig = inspect.signature(_list_fn)
            di_kwargs = {dp.name: kwargs[dp.name] for dp in _target_deps if dp.name in kwargs}

            # Build call kwargs with search filter
            call_kwargs = dict(di_kwargs)
            page_param, ps_param = find_pagination_params(_list_fn)
            if ps_param:
                call_kwargs[ps_param] = 50
            if page_param:
                call_kwargs[page_param] = 1
            if q and _search_param and _search_param in sig.parameters:
                call_kwargs[_search_param] = q

            # Only pass kwargs the function accepts
            valid_kwargs = {k: v for k, v in call_kwargs.items() if k in sig.parameters}
            result = _list_fn(**valid_kwargs)
            items = result.items if isinstance(result, Page) else (result if isinstance(result, list) else [])

            # Build option HTML
            html_parts = []
            seen_ids: set[str] = set()
            for item in items:
                item_id = str(item.get("id") if isinstance(item, dict) else getattr(item, "id", ""))
                item_label = str(item.get(_display) if isinstance(item, dict) else getattr(item, _display, ""))
                is_selected = item_id in selected_ids
                sel = " selected" if is_selected else ""
                html_parts.append(f'<wa-option value="{item_id}"{sel}>{item_label}</wa-option>')
                seen_ids.add(item_id)

            # Fetch any selected items not in search results
            missing_ids = [sid for sid in selected_ids if sid not in seen_ids]
            if missing_ids and _target.get_fn:
                for mid in missing_ids:
                    try:
                        get_kwargs = dict(di_kwargs)
                        id_p = _target.id_param_name or "id"
                        get_kwargs[id_p] = _coerce_id(mid, _target.get_fn, id_p)
                        get_sig = inspect.signature(_target.get_fn)
                        valid_get = {k: v for k, v in get_kwargs.items() if k in get_sig.parameters}
                        sel_item = _target.get_fn(**valid_get)
                        if sel_item:
                            item_label = str(sel_item.get(_display) if isinstance(sel_item, dict) else getattr(sel_item, _display, ""))
                            html_parts.insert(0, f'<wa-option value="{mid}" selected>{item_label}</wa-option>')
                    except Exception:
                        html_parts.insert(0, f'<wa-option value="{mid}" selected>{mid}</wa-option>')

            return HTMLResponse(content="\n".join(html_parts))

        _inject_depends(options_handler, target_deps)
        router.add_api_route(
            f"/options/{rel_field.name}",
            options_handler,
            methods=["GET"],
            response_class=HTMLResponse,
        )


def build_resource_router(resource: Resource, render, site=None) -> APIRouter:
    router = APIRouter(prefix=f"/{resource.name}", tags=[resource.name])

    id_param = resource.id_param_name

    # Setup relationship auto-choices on all field lists
    if site:
        _setup_relationships(resource.create_fields, site)
        _setup_relationships(resource.update_fields, site)
        _setup_relationships(resource.detail_fields, site)

        # Register /options/{field_name} endpoint for each relationship field
        _register_options_endpoints(router, resource, site, render)

    if resource.list_fn:
        list_deps = resource.get_depends_params("list")
        page_param, page_size_param = find_pagination_params(resource.list_fn)
        sort_param = find_sort_param(resource.list_fn)

        async def list_page(request: Request, _res=resource):
            return render("list.html", resource=_res, request=request)

        async def rows(request: Request, _res=resource, _deps=list_deps,
                       _page_p=page_param, _ps_p=page_size_param, _sort_p=sort_param, **kwargs):
            from typeboard.pagination import Page

            page = int(request.query_params.get("page", "1"))
            page_size = int(request.query_params.get("page_size", "25"))
            sort = request.query_params.get("sort")

            fn_kwargs: dict[str, Any] = {}

            # DI params
            for dp in _deps:
                if dp.name in kwargs:
                    fn_kwargs[dp.name] = kwargs[dp.name]

            # Pagination
            if _page_p:
                fn_kwargs[_page_p] = page
            if _ps_p:
                fn_kwargs[_ps_p] = page_size

            # Sort
            if sort and _sort_p:
                fn_kwargs[_sort_p] = sort

            # Filters
            for ff in _res.filter_fields:
                val = request.query_params.get(ff.name)
                if val:
                    fn_kwargs[ff.name] = val

            # Only pass kwargs the function actually accepts
            sig = inspect.signature(_res.list_fn)
            valid_kwargs = {k: v for k, v in fn_kwargs.items() if k in sig.parameters}
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

        _inject_depends(rows, list_deps)

        router.add_api_route("/", list_page, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/rows", rows, methods=["GET"], response_class=HTMLResponse)

    if resource.create_fn:
        create_deps = resource.get_depends_params("create")
        create_form_choices_deps = _collect_choices_deps(resource.create_fields)
        # Merge create deps + choices deps (deduped)
        create_form_deps = list(create_deps)
        seen_dep_names = {dp.name for dp in create_form_deps}
        for dp in create_form_choices_deps:
            if dp.name not in seen_dep_names:
                create_form_deps.append(dp)
                seen_dep_names.add(dp.name)

        async def create_form(request: Request, _res=resource, _deps=create_form_deps, **kwargs):
            fields = _res.create_fields
            di_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}
            _resolve_choices(fields, di_kwargs)
            return render("form.html", resource=_res, request=request, mode="create", fields=fields, values={}, errors=[])

        async def create_submit(request: Request, _res=resource, _deps=create_deps, **kwargs):
            from pydantic import BaseModel
            fields = _res.create_fields
            form_data = await request.form()
            values = {}
            for field in fields:
                if field.hidden or field.read_only:
                    continue
                if field.widget == "multiselect":
                    raw = form_data.getlist(field.name)
                    values[field.name] = _coerce(raw, field.python_type) if raw else []
                    continue
                raw = form_data.get(field.name)
                if raw is None or raw == "":
                    if not field.required:
                        values[field.name] = field.default
                    continue
                values[field.name] = _coerce(raw, field.python_type)

            fn_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}

            sig = inspect.signature(_res.create_fn)
            params = list(sig.parameters.values())
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
                fn_kwargs[name] = model_instance
            else:
                fn_kwargs.update(values)

            result = _res.create_fn(**fn_kwargs)

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

        _inject_depends(create_form, create_form_deps)
        _inject_depends(create_submit, create_deps)
        router.add_api_route("/new", create_form, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/new", create_submit, methods=["POST"])

    if resource.get_fn:
        get_deps = resource.get_depends_params("get")
        # Merge in DI deps needed for relationship resolution on the detail page
        detail_rel_deps = _collect_relationship_deps(resource.detail_fields, site) if site else []
        detail_deps = list(get_deps)
        seen_dep_names = {dp.name for dp in detail_deps}
        for dp in detail_rel_deps:
            if dp.name not in seen_dep_names:
                detail_deps.append(dp)
                seen_dep_names.add(dp.name)

        async def detail_page(request: Request, id: str, _res=resource, _deps=get_deps, _all_deps=detail_deps, _id_p=id_param, _site=site, **kwargs):
            coerced_id = _coerce_id(id, _res.get_fn, _id_p)
            fn_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}
            fn_kwargs[_id_p or "id"] = coerced_id
            item = _res.get_fn(**fn_kwargs)
            # Resolve relationship IDs to display names
            if _site:
                all_di = {dp.name: kwargs[dp.name] for dp in _all_deps if dp.name in kwargs}
                item = _resolve_detail_relationships(item, _res.detail_fields, _site, all_di)
            return render("detail.html", resource=_res, request=request, id=id, item=item, columns=_res.detail_fields)

        _inject_depends(detail_page, detail_deps)
        router.add_api_route("/{id}", detail_page, methods=["GET"], response_class=HTMLResponse)

    if resource.update_fn:
        update_deps = resource.get_depends_params("update")
        # edit_form needs get_fn deps + choices deps
        edit_get_deps = resource.get_depends_params("get") if resource.get_fn else []
        edit_choices_deps = _collect_choices_deps(resource.update_fields)
        # Merge get deps + choices deps (deduped)
        edit_form_deps = list(edit_get_deps)
        seen_edit_dep_names = {dp.name for dp in edit_form_deps}
        for dp in edit_choices_deps:
            if dp.name not in seen_edit_dep_names:
                edit_form_deps.append(dp)
                seen_edit_dep_names.add(dp.name)

        async def edit_form(request: Request, id: str, _res=resource, _deps=edit_form_deps, _get_deps=edit_get_deps, _id_p=id_param, **kwargs):
            fn_kwargs = {dp.name: kwargs[dp.name] for dp in _get_deps if dp.name in kwargs}
            coerced_id = _coerce_id(id, _res.get_fn, _id_p) if _res.get_fn else int(id)
            fn_kwargs[_id_p or "id"] = coerced_id
            item = _res.get_fn(**fn_kwargs) if _res.get_fn else None
            fields = _res.update_fields
            di_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}
            _resolve_choices(fields, di_kwargs)
            values = {}
            if item:
                for f in fields:
                    if isinstance(item, dict):
                        values[f.name] = item.get(f.name, f.default)
                    else:
                        values[f.name] = getattr(item, f.name, f.default)
            return render("form.html", resource=_res, request=request, mode="edit", id=id, fields=fields, values=values, errors=[])

        _inject_depends(edit_form, edit_form_deps)

        async def edit_submit(request: Request, id: str, _res=resource, _deps=update_deps, _id_p=id_param, **kwargs):
            from pydantic import BaseModel
            fields = _res.update_fields
            form_data = await request.form()
            values = {}
            for field in fields:
                if field.hidden or field.read_only:
                    continue
                if field.widget == "multiselect":
                    raw = form_data.getlist(field.name)
                    values[field.name] = _coerce(raw, field.python_type) if raw else []
                    continue
                raw = form_data.get(field.name)
                if raw is None or raw == "":
                    if not field.required:
                        values[field.name] = field.default
                    continue
                values[field.name] = _coerce(raw, field.python_type)

            coerced_id = _coerce_id(id, _res.update_fn, _id_p)
            fn_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}
            fn_kwargs[_id_p or "id"] = coerced_id

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
                fn_kwargs[name] = model_instance
            else:
                fn_kwargs.update(values)

            _res.update_fn(**fn_kwargs)

            return RedirectResponse(
                url=f"{request.scope.get('root_path', '')}/{_res.name}/{id}",
                status_code=303,
            )

        _inject_depends(edit_submit, update_deps)
        router.add_api_route("/{id}/edit", edit_form, methods=["GET"], response_class=HTMLResponse)
        router.add_api_route("/{id}/edit", edit_submit, methods=["POST"])

    if resource.delete_fn:
        delete_deps = resource.get_depends_params("delete")

        async def delete_item(request: Request, id: str, _res=resource, _deps=delete_deps, _id_p=id_param, **kwargs):
            coerced_id = _coerce_id(id, _res.delete_fn, _id_p)
            fn_kwargs = {dp.name: kwargs[dp.name] for dp in _deps if dp.name in kwargs}
            fn_kwargs[_id_p or "id"] = coerced_id
            _res.delete_fn(**fn_kwargs)
            return HTMLResponse(content="", headers={"HX-Redirect": f"{request.scope.get('root_path', '')}/{_res.name}/"})

        _inject_depends(delete_item, delete_deps)
        router.add_api_route("/{id}", delete_item, methods=["DELETE"])

    return router


def build_app(site) -> FastAPI:
    admin_app = FastAPI(title=site.title, docs_url=None, redoc_url=None)

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
        resource_router = build_resource_router(resource, render, site=site)
        main_router.include_router(resource_router)

    admin_app.include_router(main_router)
    return admin_app
