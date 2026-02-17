from typing import Callable

from typeboard.resource import Resource


class AdminSite:
    def __init__(
        self,
        title: str = "Admin",
        auth_dependency: Callable | None = None,
    ):
        self.title = title
        self.auth_dependency = auth_dependency
        self.resources: dict[str, Resource] = {}

    def resource(
        self,
        name: str,
        *,
        list: Callable | None = None,
        get: Callable | None = None,
        create: Callable | None = None,
        update: Callable | None = None,
        delete: Callable | None = None,
    ) -> Resource:
        res = Resource(
            name=name,
            list_fn=list,
            get_fn=get,
            create_fn=create,
            update_fn=update,
            delete_fn=delete,
        )
        self.resources[name] = res
        return res

    def as_asgi(self):
        from typeboard.routing import build_app
        return build_app(self)
