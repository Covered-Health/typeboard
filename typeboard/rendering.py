from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_renderer(site):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )

    def item_value(item, field_name):
        if isinstance(item, dict):
            return item.get(field_name, "")
        return getattr(item, field_name, "")

    def item_id(item, field_name=None):
        if field_name:
            if isinstance(item, dict):
                return item.get(field_name, "")
            return getattr(item, field_name, "")
        if isinstance(item, dict):
            return item.get("id", item.get("pk", ""))
        return getattr(item, "id", getattr(item, "pk", ""))

    env.globals["item_value"] = item_value
    env.globals["item_id"] = item_id

    def render(template_name: str, *, request: Any, **context: Any) -> HTMLResponse:
        template = env.get_template(template_name)
        base_path = request.scope.get("root_path", "")
        html = template.render(
            site=site,
            base_path=base_path,
            request=request,
            **context,
        )
        return HTMLResponse(content=html)

    return render
