# Bootstrap Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Web Awesome with Bootstrap 5.3 + Font Awesome + Tom Select across all typeboard templates, switching from sidebar to horizontal navbar navigation.

**Architecture:** Templates use Jinja2 with HTMX. All components are Web Awesome custom elements (`wa-*`) that become standard HTML with Bootstrap CSS classes. Tom Select enhances native `<select multiple>` elements for searchable multiselect. The `/options/{field_name}` endpoint switches from returning `<wa-option>` HTML to JSON.

**Tech Stack:** Bootstrap 5.3.8, Font Awesome 6.7.2, Tom Select 2.4.3 (Bootstrap 5 theme), HTMX 2.0.4 (unchanged)

**Design doc:** `docs/plans/2026-02-19-bootstrap-migration-design.md`

---

### Task 1: base.html — CDN links, navbar, CSS, JS

**Files:**
- Modify: `typeboard/templates/base.html`

**Step 1: Replace CDN links in `<head>`**

Remove the 3 Web Awesome CDN lines and replace with Bootstrap CSS, Font Awesome CSS, Tom Select CSS:

```html
<!-- REMOVE these 3 lines -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/styles/themes/default.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/styles/webawesome.css" />
<script type="module" src="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/webawesome.loader.js"></script>

<!-- ADD these -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/css/tom-select.bootstrap5.min.css" rel="stylesheet">
```

Add Bootstrap JS bundle and Tom Select JS before `</body>`:

```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/js/tom-select.complete.min.js"></script>
```

**Step 2: Change theme attribute**

Change `<body class="wa-{{ site.theme.mode }}">` to just `<body>` and change `<html lang="en">` to:

```html
<html lang="en" data-bs-theme="{{ site.theme.mode }}">
```

**Step 3: Replace loading bar**

Replace:
```html
<div id="loading-bar"><wa-progress-bar indeterminate></wa-progress-bar></div>
```

With:
```html
<div id="loading-bar">
    <div class="progress" style="height: 3px; border-radius: 0;">
        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
    </div>
</div>
```

**Step 4: Replace header + sidebar with Bootstrap navbar**

Remove the entire `<header class="top-header">...</header>` and `<nav class="sidebar">...</nav>` and the wrapping `<div class="app-layout">`.

Replace with a Bootstrap navbar before `<main>`:

```html
<nav class="navbar navbar-expand-lg bg-body-tertiary border-bottom mb-0">
    <div class="container-fluid">
        <a class="navbar-brand" href="{{ base_path }}/">
            {% if site.logo_url %}
            <img src="{% if site.logo_url.startswith('/') %}{{ base_path }}{{ site.logo_url }}{% else %}{{ site.logo_url }}{% endif %}"
                 alt="{{ site.title }}" height="{{ site.logo_height }}">
            {% else %}
            {{ site.title }}
            {% endif %}
        </a>
        <button class="navbar-toggler" type="button"
                data-bs-toggle="collapse" data-bs-target="#adminNav"
                aria-controls="adminNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="adminNav">
            <ul class="navbar-nav">
                {% for section_name, resource_names in site.sidebar_sections %}
                {% if section_name and resource_names | length > 3 %}
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button"
                       data-bs-toggle="dropdown" aria-expanded="false">
                        {{ section_name }}
                    </a>
                    <ul class="dropdown-menu">
                        {% for name in resource_names %}
                        <li>
                            <a class="dropdown-item{% if resource is defined and resource.id == name %} active{% endif %}"
                               href="{{ base_path }}/{{ name }}/">
                                {{ site.resources[name].label }}
                            </a>
                        </li>
                        {% endfor %}
                    </ul>
                </li>
                {% else %}
                {% for name in resource_names %}
                <li class="nav-item">
                    <a class="nav-link{% if resource is defined and resource.id == name %} active{% endif %}"
                       href="{{ base_path }}/{{ name }}/">
                        {{ site.resources[name].label }}
                    </a>
                </li>
                {% endfor %}
                {% endif %}
                {% endfor %}
            </ul>
        </div>
    </div>
</nav>
```

And the main content becomes:

```html
<main class="container-fluid py-4">
    {% block content %}{% endblock %}
</main>
```

**Step 5: Replace the `<style>` block**

Remove ALL custom CSS. Replace with only what's still needed:

```css
/* -- Loading bar -- */
#loading-bar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    z-index: 9999;
    display: none;
}
#loading-bar.active { display: block; }

/* -- Detail View grid -- */
.detail-grid {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 0;
}
.detail-grid dt, .detail-grid dd {
    padding: 12px 0;
    border-bottom: 1px solid var(--bs-border-color);
}
.detail-grid dt:last-of-type, .detail-grid dd:last-of-type { border-bottom: none; }
.detail-grid dt {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--bs-secondary-color);
}
.detail-grid dd {
    color: var(--bs-body-color);
    font-weight: 400;
}

/* -- Fade-in -- */
.fade-in { animation: fadeIn 200ms ease-out; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}
```

**Step 6: Replace the JS**

Remove the `toggleSidebar()` function and its localStorage logic. Keep the loading bar HTMX listeners and admin token injection. The JS becomes:

```javascript
document.addEventListener('htmx:configRequest', function(event) {
    var token = localStorage.getItem('admin_access_token');
    if (token) {
        event.detail.headers['Authorization'] = 'Bearer ' + token;
    }
});
document.addEventListener('DOMContentLoaded', function() {
    var bar = document.getElementById('loading-bar');
    document.body.addEventListener('htmx:beforeRequest', function() {
        bar.classList.add('active');
    });
    document.body.addEventListener('htmx:afterRequest', function() {
        bar.classList.remove('active');
    });
});
```

**Step 7: Verify visually**

Run the app and confirm the navbar renders, collapses on mobile viewport, and the loading bar works.

**Step 8: Commit**

```bash
git add typeboard/templates/base.html
git commit -m "feat: replace Web Awesome with Bootstrap 5.3 in base template

Switch from sidebar to horizontal Bootstrap navbar with responsive
collapse. Replace all CDN links. Add Tom Select and Font Awesome CDNs.
Remove sidebar toggle JS and custom CSS replaced by Bootstrap utilities."
```

---

### Task 2: index.html — Welcome page

**Files:**
- Modify: `typeboard/templates/index.html`

**Step 1: Update welcome page classes**

Replace:
```html
<div class="welcome fade-in">
```

With:
```html
<div class="d-flex flex-column align-items-center justify-content-center fade-in" style="min-height: 60vh;">
```

Add Bootstrap text classes to the children:

```html
<h1 class="fs-3 fw-semibold mb-2">{{ site.title }}</h1>
<p class="text-body-secondary">Select a resource from the menu to get started.</p>
```

(Change "sidebar" to "menu" in the text since there's no sidebar anymore.)

**Step 2: Commit**

```bash
git add typeboard/templates/index.html
git commit -m "feat: update welcome page to Bootstrap utilities"
```

---

### Task 3: list.html — List view with filters and table

**Files:**
- Modify: `typeboard/templates/list.html`

**Step 1: Replace all components**

Full new content:

```html
{% extends "base.html" %}
{% block content %}
<div class="fade-in">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="fs-4 fw-semibold mb-0">{{ resource.label }}</h1>
        <div class="d-flex gap-2 align-items-center">
            {% if resource.create_fn %}
            <a class="btn btn-primary btn-sm" href="{{ base_path }}/{{ resource.id }}/new">
                <i class="fa-solid fa-plus me-1"></i>
                New
            </a>
            {% endif %}
        </div>
    </div>

    {% if resource.filter_fields %}
    <form class="d-flex flex-wrap gap-2 mb-3 align-items-end"
          hx-get="{{ base_path }}/{{ resource.id }}/rows" hx-target="#table-body" hx-trigger="submit" hx-swap="innerHTML">
        {% for field in resource.filter_fields %}
        <div>
            {% if field.filter == "search" %}
            <input type="search" class="form-control form-control-sm" name="{{ field.name }}"
                   placeholder="Search {{ field.label | lower }}..."
                   hx-get="{{ base_path }}/{{ resource.id }}/rows"
                   hx-target="#table-body" hx-swap="innerHTML"
                   hx-trigger="input changed delay:300ms, search"
                   hx-include="closest form">
            {% elif field.filter == "select" %}
            <select class="form-select form-select-sm" name="{{ field.name }}"
                    hx-get="{{ base_path }}/{{ resource.id }}/rows"
                    hx-target="#table-body" hx-swap="innerHTML"
                    hx-trigger="change"
                    hx-include="closest form">
                <option value="">All {{ field.label | lower }}</option>
                {% if field.enum_choices %}
                {% for value, label in field.enum_choices %}
                <option value="{{ value }}">{{ label }}</option>
                {% endfor %}
                {% endif %}
            </select>
            {% else %}
            <input type="text" class="form-control form-control-sm" name="{{ field.name }}"
                   placeholder="{{ field.label }}"
                   hx-get="{{ base_path }}/{{ resource.id }}/rows"
                   hx-target="#table-body" hx-swap="innerHTML"
                   hx-trigger="input changed delay:300ms"
                   hx-include="closest form">
            {% endif %}
        </div>
        {% endfor %}
    </form>
    {% endif %}

    <div class="table-responsive">
        <table class="table table-striped table-hover table-sm">
            <thead>
                <tr>
                    {% for col in resource.columns %}
                    {% if col.column and not col.hidden %}
                    <th>
                        <a href="#" class="text-decoration-none text-body-secondary"
                           hx-get="{{ base_path }}/{{ resource.id }}/rows?sort={{ col.name }}"
                           hx-target="#table-body" hx-swap="innerHTML">
                            {{ col.label }}
                        </a>
                    </th>
                    {% endif %}
                    {% endfor %}
                    {% if resource.delete_fn %}
                    <th class="text-end">Actions</th>
                    {% endif %}
                </tr>
            </thead>
            <tbody id="table-body"
                   hx-get="{{ base_path }}/{{ resource.id }}/rows"
                   hx-trigger="load"
                   hx-swap="innerHTML">
                <tr><td colspan="100" class="text-center text-body-secondary p-5">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

Note: The `wa-clear` HTMX trigger on search inputs becomes the native `search` event (fired when a user clears a search input via the browser's built-in X button).

**Step 2: Commit**

```bash
git add typeboard/templates/list.html
git commit -m "feat: migrate list template to Bootstrap"
```

---

### Task 4: detail.html — Detail view

**Files:**
- Modify: `typeboard/templates/detail.html`

**Step 1: Replace all components**

Full new content:

```html
{% extends "base.html" %}
{% block content %}
<div class="fade-in">
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            {% if resource.list_fn %}
            <li class="breadcrumb-item"><a href="{{ base_path }}/{{ resource.id }}/">{{ resource.label }}</a></li>
            {% endif %}
            <li class="breadcrumb-item active" aria-current="page">{{ display_name or id }}</li>
        </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="fs-4 fw-semibold mb-0">{{ display_name or (resource.label ~ " #" ~ id) }}</h1>
        <div class="d-flex gap-2 align-items-center">
            {% if resource.update_fn %}
            <a class="btn btn-primary btn-sm" href="{{ base_path }}/{{ resource.id }}/{{ id }}/edit">
                <i class="fa-solid fa-pen me-1"></i>
                Edit
            </a>
            {% endif %}
            {% if resource.list_fn %}
            <a class="btn btn-outline-secondary btn-sm" href="{{ base_path }}/{{ resource.id }}/">
                <i class="fa-solid fa-arrow-left me-1"></i>
                Back to list
            </a>
            {% endif %}
        </div>
    </div>

    {% if item %}
    <div class="card">
        <div class="card-body">
            <dl class="detail-grid">
                {% for col in columns %}
                {% if not col.hidden %}
                <dt>{{ col.label }}</dt>
                <dd>
                    {% set val = item_value(item, col.name) %}
                    {% set rel_target = relationship_targets.get(col.name) if relationship_targets is defined else None %}
                    {% if val is iterable and val is not string and val is not mapping %}
                    <div class="d-flex gap-1 flex-wrap">
                        {% for v in val %}
                        {% if rel_target and v is iterable and v is not string %}
                        <a href="{{ base_path }}/{{ rel_target }}/{{ v[0] }}" class="text-decoration-none">
                            <span class="badge text-bg-secondary rounded-pill">{{ v[1] }}</span>
                        </a>
                        {% else %}
                        <span class="badge text-bg-secondary rounded-pill">{{ v }}</span>
                        {% endif %}
                        {% endfor %}
                        {% if not val %}<span class="text-body-secondary">None</span>{% endif %}
                    </div>
                    {% else %}
                    {% if rel_target and val is iterable and val is not string %}
                    <a href="{{ base_path }}/{{ rel_target }}/{{ val[0] }}">{{ val[1] }}</a>
                    {% else %}
                    {{ val }}
                    {% endif %}
                    {% endif %}
                </dd>
                {% endif %}
                {% endfor %}
            </dl>
        </div>
    </div>
    {% else %}
    <div class="text-center text-body-secondary p-5">Record not found.</div>
    {% endif %}
</div>
{% endblock %}
```

**Step 2: Commit**

```bash
git add typeboard/templates/detail.html
git commit -m "feat: migrate detail template to Bootstrap"
```

---

### Task 5: form.html — Create/edit form

**Files:**
- Modify: `typeboard/templates/form.html`

**Step 1: Replace all components**

Full new content:

```html
{% extends "base.html" %}
{% block content %}
<div class="fade-in">
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            {% if resource.list_fn %}
            <li class="breadcrumb-item"><a href="{{ base_path }}/{{ resource.id }}/">{{ resource.label }}</a></li>
            {% endif %}
            <li class="breadcrumb-item active" aria-current="page">{% if mode == "create" %}New{% else %}Edit {{ display_name or id }}{% endif %}</li>
        </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="fs-4 fw-semibold mb-0">{% if mode == "create" %}New {{ resource.label }}{% else %}Edit {{ display_name or (resource.label ~ " #" ~ id) }}{% endif %}</h1>
    </div>

    {% if errors %}
    <div class="alert alert-danger mb-3">
        {% for error in errors %}
        <div>{{ error }}</div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="card">
        <div class="card-body">
            <div style="max-width: 560px;">
                <form method="post">
                    {% for field in fields %}
                    {% if not field.hidden %}
                    {% include "_field.html" %}
                    {% endif %}
                    {% endfor %}

                    <div class="d-flex gap-2 mt-4">
                        <button class="btn btn-primary" type="submit">
                            <i class="fa-solid fa-{% if mode == 'create' %}plus{% else %}floppy-disk{% endif %} me-1"></i>
                            {% if mode == "create" %}Create{% else %}Save changes{% endif %}
                        </button>
                        {% if resource.list_fn %}
                        <a class="btn btn-outline-secondary" href="{{ base_path }}/{{ resource.id }}/">Cancel</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**Step 2: Commit**

```bash
git add typeboard/templates/form.html
git commit -m "feat: migrate form template to Bootstrap"
```

---

### Task 6: _field.html — Form field widgets + Tom Select

**Files:**
- Modify: `typeboard/templates/_field.html`

**Step 1: Replace all widget implementations**

Full new content:

```html
<div class="mb-3">
    {% if field.widget == "textarea" %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <textarea class="form-control" id="field-{{ field.name }}"
              name="{{ field.name }}"
              {% if field.read_only %}disabled{% endif %}
              {% if field.required %}required{% endif %}
              placeholder="Enter {{ field.label | lower }}..."
              rows="4">{{ values.get(field.name, field.default or '') }}</textarea>

    {% elif field.widget == "checkbox" %}
    <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" role="switch"
               id="field-{{ field.name }}" name="{{ field.name }}"
               {% if values.get(field.name, field.default) %}checked{% endif %}
               {% if field.read_only %}disabled{% endif %}>
        <label class="form-check-label" for="field-{{ field.name }}">{{ field.label }}</label>
    </div>

    {% elif field.widget == "number" %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <input type="number" class="form-control" id="field-{{ field.name }}"
           name="{{ field.name }}" value="{{ values.get(field.name, field.default or '') }}"
           {% if field.read_only %}disabled{% endif %} {% if field.required %}required{% endif %}
           placeholder="0">

    {% elif field.widget == "date" %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <input type="date" class="form-control" id="field-{{ field.name }}"
           name="{{ field.name }}" value="{{ values.get(field.name, field.default or '') }}"
           {% if field.read_only %}disabled{% endif %} {% if field.required %}required{% endif %}>

    {% elif field.widget == "datetime" %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <input type="datetime-local" class="form-control" id="field-{{ field.name }}"
           name="{{ field.name }}" value="{{ values.get(field.name, field.default or '') }}"
           {% if field.read_only %}disabled{% endif %} {% if field.required %}required{% endif %}>

    {% elif field.widget == "multiselect" and field.relationship %}
    {% set current = values.get(field.name, []) | map('string') | list %}
    {% set select_id = "rel-" ~ field.name %}
    <label class="form-label" for="{{ select_id }}">{{ field.label }}</label>
    <select class="form-select" id="{{ select_id }}"
            name="{{ field.name }}" multiple
            {% if field.read_only %}disabled{% endif %}
            data-ts-remote="{{ base_path }}/{{ resource.id }}/options/{{ field.name }}">
        {% for value, label in field.enum_choices or [] %}
        <option value="{{ value }}" {% if value|string in current %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
    </select>

    {% elif field.widget == "multiselect" %}
    {% set current = values.get(field.name, []) | map('string') | list %}
    {% set select_id = "ms-" ~ field.name %}
    <label class="form-label" for="{{ select_id }}">{{ field.label }}</label>
    <select class="form-select" id="{{ select_id }}"
            name="{{ field.name }}" multiple
            {% if field.read_only %}disabled{% endif %}
            data-ts="true">
        {% if field.enum_choices %}
        {% for value, label in field.enum_choices %}
        <option value="{{ value }}" {% if value|string in current %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
        {% endif %}
    </select>

    {% elif field.widget == "select" %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <select class="form-select" id="field-{{ field.name }}"
            name="{{ field.name }}"
            {% if field.read_only %}disabled{% endif %} {% if field.required %}required{% endif %}>
        {% if not field.required %}<option value="">Select...</option>{% endif %}
        {% if field.enum_choices %}
        {% for value, label in field.enum_choices %}
        <option value="{{ value }}" {% if values.get(field.name) == value %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
        {% endif %}
    </select>

    {% else %}
    <label class="form-label" for="field-{{ field.name }}">{{ field.label }}</label>
    <input type="text" class="form-control" id="field-{{ field.name }}"
           name="{{ field.name }}" value="{{ values.get(field.name, field.default or '') }}"
           {% if field.read_only %}disabled{% endif %} {% if field.required %}required{% endif %}
           placeholder="Enter {{ field.label | lower }}...">
    {% endif %}
</div>
```

**Step 2: Add Tom Select initialization to base.html**

Add this script block at the end of base.html (after the Tom Select CDN script):

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Simple multiselect (local options)
    document.querySelectorAll('select[data-ts="true"]').forEach(function(el) {
        new TomSelect(el, {
            plugins: ['remove_button'],
            maxOptions: null
        });
    });

    // Relationship multiselect (remote search)
    document.querySelectorAll('select[data-ts-remote]').forEach(function(el) {
        var url = el.getAttribute('data-ts-remote');
        var token = localStorage.getItem('admin_access_token');
        new TomSelect(el, {
            plugins: ['remove_button'],
            valueField: 'value',
            labelField: 'text',
            searchField: 'text',
            maxOptions: null,
            load: function(query, callback) {
                var sep = url.indexOf('?') >= 0 ? '&' : '?';
                var selected = this.items.join(',');
                var fetchUrl = url + sep + 'q=' + encodeURIComponent(query) + '&selected=' + encodeURIComponent(selected);
                var headers = {};
                if (token) headers['Authorization'] = 'Bearer ' + token;
                fetch(fetchUrl, {headers: headers})
                    .then(function(r) { return r.json(); })
                    .then(function(data) { callback(data); })
                    .catch(function() { callback(); });
            }
        });
    });
});
```

**Step 3: Commit**

```bash
git add typeboard/templates/_field.html typeboard/templates/base.html
git commit -m "feat: migrate form fields to Bootstrap + Tom Select for multiselect"
```

---

### Task 7: _table_rows.html — Table rows and pagination

**Files:**
- Modify: `typeboard/templates/_table_rows.html`

**Step 1: Replace all components**

Full new content:

```html
{% if items %}
{% for item in items %}
<tr class="fade-in"
    {% if resource.get_fn %}
    style="cursor:pointer;"
    onclick="window.location='{{ base_path }}/{{ resource.id }}/{{ item_id(item, resource.id_param_name) }}'"
    {% endif %}>
    {% for col in columns %}
    {% if col.column and not col.hidden %}
    <td>{{ item_value(item, col.name) }}</td>
    {% endif %}
    {% endfor %}
    {% if resource.delete_fn %}
    <td class="text-end" onclick="event.stopPropagation()">
        <button class="btn btn-outline-danger btn-sm"
                hx-delete="{{ base_path }}/{{ resource.id }}/{{ item_id(item, resource.id_param_name) }}"
                hx-confirm="Are you sure you want to delete this record?"
                hx-target="closest tr"
                hx-swap="outerHTML">
            <i class="fa-solid fa-trash me-1"></i>
            Delete
        </button>
    </td>
    {% endif %}
</tr>
{% endfor %}
{% else %}
<tr><td colspan="100" class="text-center text-body-secondary p-5">No records found.</td></tr>
{% endif %}

{% if page_info and page_info.total_pages > 1 %}
<tr>
    <td colspan="100">
        <div class="d-flex justify-content-between align-items-center pt-3">
            <div>
                {% if page_info.has_prev %}
                <button class="btn btn-outline-secondary btn-sm"
                   hx-get="{{ base_path }}/{{ resource.id }}/rows?page={{ page_info.page - 1 }}"
                   hx-target="#table-body"
                   hx-swap="innerHTML">
                    <i class="fa-solid fa-chevron-left me-1"></i>
                    Previous
                </button>
                {% endif %}
            </div>
            <span class="text-body-secondary small">Page {{ page_info.page }} of {{ page_info.total_pages }} &middot; {{ page_info.total }} records</span>
            <div>
                {% if page_info.has_next %}
                <button class="btn btn-outline-secondary btn-sm"
                   hx-get="{{ base_path }}/{{ resource.id }}/rows?page={{ page_info.page + 1 }}"
                   hx-target="#table-body"
                   hx-swap="innerHTML">
                    Next
                    <i class="fa-solid fa-chevron-right ms-1"></i>
                </button>
                {% endif %}
            </div>
        </div>
    </td>
</tr>
{% endif %}
```

**Step 2: Commit**

```bash
git add typeboard/templates/_table_rows.html
git commit -m "feat: migrate table rows and pagination to Bootstrap"
```

---

### Task 8: routing.py — Options endpoint returns JSON

**Files:**
- Modify: `typeboard/routing.py`

**Step 1: Change the options endpoint response format**

In the `_register_options_endpoints` function, find the `options_handler` inner function. Change it to return JSON instead of `<wa-option>` HTML.

Replace the HTML building section (the `html_parts` list assembly and `HTMLResponse` return) with:

```python
from fastapi.responses import JSONResponse

# Build JSON response
results = []
seen_ids: set[str] = set()
for item in items:
    item_id = str(item.get(_id_field) if isinstance(item, dict) else getattr(item, _id_field, ""))
    item_label = str(item.get(_display) if isinstance(item, dict) else getattr(item, _display, ""))
    results.append({"value": item_id, "text": item_label})
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
                results.insert(0, {"value": mid, "text": item_label})
        except Exception:
            results.insert(0, {"value": mid, "text": mid})

return JSONResponse(content=results)
```

Also update the `response_class` in the route registration from `HTMLResponse` to `JSONResponse`:

```python
router.add_api_route(
    f"/options/{rel_field.name}",
    options_handler,
    methods=["GET"],
    response_class=JSONResponse,
)
```

Add the `JSONResponse` import at the top of the file (alongside the existing `HTMLResponse` import).

**Step 2: Commit**

```bash
git add typeboard/routing.py
git commit -m "feat: change options endpoint to return JSON for Tom Select"
```

---

### Task 9: Delete WEB_AWESOME.md

**Files:**
- Delete: `WEB_AWESOME.md`

**Step 1: Remove the file**

```bash
cd /path/to/typeboard
git rm WEB_AWESOME.md
```

**Step 2: Commit**

```bash
git commit -m "chore: remove Web Awesome reference doc"
```

---

### Task 10: Manual verification

**Step 1: Run the app and verify all views**

Check each page type:
- Home/index page — navbar with logo, responsive collapse on mobile
- List page — filters, table with striped rows and hover, pagination, sort headers
- Detail page — breadcrumb, badges for list values, relationship links
- Create form — all field types render (text, number, date, select, multiselect, switch)
- Edit form — values pre-populated, multiselect with Tom Select shows selected items
- Delete — confirmation dialog from HTMX works
- Dark mode — if configured, all components respect `data-bs-theme="dark"`

**Step 2: Check Tom Select specifically**
- Enum multiselect: options filter as you type, pills display, remove button works
- Relationship multiselect: typing triggers remote fetch, selected items persist, pills display
