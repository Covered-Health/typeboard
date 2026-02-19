# Design: Migrate Typeboard from Web Awesome to Bootstrap 5.3

## Overview

Replace Web Awesome (custom web components library) with Bootstrap 5.3 + Tom Select for the typeboard admin framework. Use Bootstrap's navbar with horizontal responsive navigation instead of the current sidebar layout.

## CDN Dependencies

### Remove
- `@awesome.me/webawesome@3.2.1` theme CSS, webawesome.css, webawesome.loader.js

### Add
- Bootstrap 5.3.8 CSS: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css`
- Bootstrap 5.3.8 JS bundle: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js`
- Font Awesome 6 free CDN (WA bundled FA icons; keeping FA avoids renaming all icons)
- Tom Select 2.4.3 Bootstrap 5 CSS: `https://cdnjs.cloudflare.com/ajax/libs/tom-select/2.4.3/css/tom-select.bootstrap5.min.css`
- Tom Select 2.4.3 JS: `https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/js/tom-select.complete.min.js`
- HTMX stays as-is

## Layout: Sidebar + Header → Bootstrap Navbar

### Current
- Custom 52px top header with logo + hamburger toggle
- 240px sticky sidebar with section labels + nav links
- Sidebar collapses via JS toggle + CSS transition

### New
- Single Bootstrap `navbar navbar-expand-lg` with:
  - Brand/logo on the left
  - Hamburger toggler for mobile collapse
  - Horizontal nav links (`.navbar-nav`)
  - Sidebar section labels become either:
    - **Dropdowns** (if section has 4+ items) via `nav-item dropdown`
    - **Inline nav items** (if section has 1-3 items) with a visual divider or label
- Removes: sidebar HTML, sidebar CSS, sidebar toggle JS, localStorage collapse state

### Navbar structure
```html
<nav class="navbar navbar-expand-lg bg-body-tertiary border-bottom">
  <div class="container-fluid">
    <a class="navbar-brand" href="...">Logo/Title</a>
    <button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#adminNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="adminNav">
      <ul class="navbar-nav">
        <!-- sections with few items: inline -->
        <li class="nav-item"><a class="nav-link active" href="...">Resource</a></li>
        <!-- sections with many items: dropdown -->
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" data-bs-toggle="dropdown">Section</a>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="...">Resource</a></li>
          </ul>
        </li>
      </ul>
    </div>
  </div>
</nav>
```

## Component Mapping

| Web Awesome | Bootstrap | Notes |
|---|---|---|
| `wa-button variant="brand"` | `<a class="btn btn-primary">` | |
| `wa-button variant="danger" appearance="outlined"` | `<a class="btn btn-outline-danger">` | |
| `wa-button appearance="outlined"` | `<a class="btn btn-outline-secondary">` | |
| `wa-button size="small"` | `btn-sm` | |
| `wa-icon name="X" slot="start/end"` | `<i class="fa-solid fa-X me-1">` / `ms-1` | Keep FA icon names |
| `wa-input type="T" label="L"` | `<label class="form-label">L</label><input type="T" class="form-control">` | Labels become separate elements |
| `wa-input size="small"` | `form-control-sm` | |
| `wa-input with-clear` | Custom clear button via small JS | |
| `wa-textarea` | `<textarea class="form-control">` | |
| `wa-select` / `wa-option` | `<select class="form-select"><option>` | |
| `wa-select size="small"` | `form-select-sm` | |
| `wa-select multiple with-clear pill` | `<select multiple>` + Tom Select init | |
| `wa-switch` | `<div class="form-check form-switch"><input type="checkbox" class="form-check-input" role="switch">` | |
| `wa-card` | `<div class="card"><div class="card-body">` | |
| `wa-breadcrumb` | `<nav aria-label="breadcrumb"><ol class="breadcrumb">` | |
| `wa-breadcrumb-item href="X"` | `<li class="breadcrumb-item"><a href="X">` | |
| `wa-breadcrumb-item` (active) | `<li class="breadcrumb-item active" aria-current="page">` | |
| `wa-callout variant="danger"` | `<div class="alert alert-danger">` | |
| `wa-tag size="small" variant="neutral" pill` | `<span class="badge text-bg-secondary rounded-pill">` | |
| `wa-progress-bar indeterminate` | `<div class="progress"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:100%">` | |

## HTMX Event Changes

| Web Awesome Event | Standard Replacement |
|---|---|
| `wa-change` (on wa-select) | `change` (on native select) |
| `wa-clear` (on wa-input with-clear) | Custom: dispatch `input` event after clearing |

For Tom Select enhanced selects, use Tom Select's `onChange` callback to trigger HTMX requests if needed.

## CSS Variable Mapping

| Web Awesome | Bootstrap |
|---|---|
| `--wa-color-neutral-15` | `var(--bs-body-color)` |
| `--wa-color-neutral-40` | `var(--bs-secondary-color)` |
| `--wa-color-neutral-50` | `var(--bs-tertiary-color)` |
| `--wa-color-neutral-85` | `var(--bs-border-color)` |
| `--wa-color-neutral-90` | `var(--bs-tertiary-bg)` |
| `--wa-color-neutral-95` | `var(--bs-body-bg)` |
| `--wa-color-neutral-97` | `var(--bs-tertiary-bg)` |
| `--wa-color-neutral-100` | `var(--bs-body-bg)` |
| `--wa-color-brand-50/60` | `var(--bs-primary)` |
| `--wa-font-sans` | `var(--bs-body-font-family)` |
| `--wa-border-radius-medium/large` | `var(--bs-border-radius)` |

## Custom CSS replaced by Bootstrap utilities

| Current Custom CSS | Bootstrap Classes |
|---|---|
| Table styling (striped, hover, borders) | `table table-striped table-hover table-sm` |
| Table responsive scroll | `table-responsive` |
| `.page-header` flex layout | `d-flex justify-content-between align-items-center mb-4` |
| `.actions` flex gap | `d-flex gap-2 align-items-center` |
| `.filters` flex wrap gap | `d-flex flex-wrap gap-2 mb-3 align-items-end` |
| `.form-field` margin | `mb-3` |
| `.form-actions` flex gap | `d-flex gap-2 mt-4` |
| `.form-container` max-width | `mx-auto` + `style="max-width:560px"` or Bootstrap column |
| `.pagination` flex layout | `d-flex justify-content-between align-items-center pt-3` |
| `.empty-state` centered text | `text-center text-body-secondary p-5` |
| `.welcome` centering | `d-flex flex-column align-items-center justify-content-center` + `min-vh-75` |
| `*` box-sizing reset | Bootstrap's reboot handles this |
| Body font/bg/color | Bootstrap's reboot + body bg/color |

## Custom CSS that remains

- **Detail grid** (`grid-template-columns: 160px 1fr` for dt/dd) - no Bootstrap equivalent
- **Fade-in animation** (entry animation, not Bootstrap's toggle-based fade)
- **Loading bar positioning** (fixed top, z-index)
- Minor tweaks (link colors, transitions)

## Tom Select Integration

### Simple multiselect (enum choices, no remote)
- Render `<select multiple class="form-select" data-ts="true">`
- Init on DOMContentLoaded: `document.querySelectorAll('[data-ts]').forEach(el => new TomSelect(el, {plugins: ['remove_button']}))`
- Local filtering handled natively by Tom Select

### Relationship multiselect (remote search via HTMX endpoint)
- Render `<select multiple class="form-select" data-ts-remote="true" data-ts-url="/options/field_name">`
- Init with Tom Select's `load` function pointing at the existing endpoint
- The `/options/{field_name}` endpoint changes from returning `<wa-option>` HTML to returning JSON: `[{"value": "1", "text": "Label"}]`

### Filter selects (list page)
- Simple single selects in filters stay as native `<select class="form-select form-select-sm">` (no Tom Select needed)

## Python File Changes

### theme.py
- Mode values stay `"light"` / `"dark"`
- Applied as `data-bs-theme="{{ site.theme.mode }}"` on `<html>` instead of `class="wa-{{ site.theme.mode }}"` on `<body>`

### routing.py
- `/options/{field_name}` endpoint: return JSON instead of `<wa-option>` HTML
- Response format: `[{"value": "id", "text": "label"}]`

### WEB_AWESOME.md
- Delete this file

## Files Changed

1. **base.html** - CDN links, navbar layout, CSS, JS
2. **index.html** - Minor class updates
3. **list.html** - All components + utilities
4. **detail.html** - Breadcrumb, buttons, card, tags
5. **form.html** - Breadcrumb, callout, card, buttons
6. **_field.html** - All form widgets, Tom Select data attrs
7. **_table_rows.html** - Buttons, icons, pagination
8. **routing.py** - Options endpoint JSON response
9. **theme.py** - No code change needed (values are the same)
10. **WEB_AWESOME.md** - Delete

## Dark Mode

Bootstrap 5.3 supports `data-bs-theme="dark"` on `<html>`. All Bootstrap components and utilities automatically respect this. Tom Select's Bootstrap 5 theme also respects it.
