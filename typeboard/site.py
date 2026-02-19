from pathlib import Path
from collections.abc import Callable

from typeboard.resource import Resource
from typeboard.theme import LIGHT, Theme


class AdminSite:
    def __init__(
        self,
        title: str = "Admin",
        logo_url: str | Path | None = None,
        logo_height: str = "28px",
        auth_dependency: Callable | None = None,
        theme: Theme | None = None,
    ):
        self.title = title
        self.logo_url = logo_url
        self.logo_height = logo_height
        self.auth_dependency = auth_dependency
        self.theme = theme or LIGHT
        self.resources: dict[str, Resource] = {}
        # Ordered list of (section_name | None, [resource_name, ...])
        self._sections: list[tuple[str | None, list[str]]] = []
        self._current_section: str | None = None

    def section(self, name: str) -> None:
        """Start a new sidebar section. Resources registered after this call
        are placed under this section heading until the next section() call."""
        self._current_section = name
        self._sections.append((name, []))

    def resource(
        self,
        id: str,
        *,
        label: str = "",
        list: Callable | None = None,
        get: Callable | None = None,
        create: Callable | None = None,
        update: Callable | None = None,
        delete: Callable | None = None,
    ) -> Resource:
        res = Resource(
            id=id,
            label=label,
            list_fn=list,
            get_fn=get,
            create_fn=create,
            update_fn=update,
            delete_fn=delete,
        )
        self.resources[id] = res
        # Place in the current section (or a default sectionless group)
        if not self._sections or self._sections[-1][0] != self._current_section:
            self._sections.append((self._current_section, []))
        self._sections[-1][1].append(id)
        return res

    @property
    def sidebar_sections(self) -> list[tuple[str | None, list[str]]]:
        """Sections with their resource names, in registration order."""
        return self._sections

    def as_asgi(self):
        from typeboard.routing import build_app
        return build_app(self)
