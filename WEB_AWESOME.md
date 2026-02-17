# Web Awesome Reference

Typeboard uses [Web Awesome](https://webawesome.com/docs/) v3.2.1 for its UI components.

**Upstream docs:** https://webawesome.com/docs/
**CDN package:** https://www.jsdelivr.com/package/npm/@awesome.me/webawesome

## CDN Setup

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/styles/themes/default.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/styles/webawesome.css" />
<script type="module" src="https://cdn.jsdelivr.net/npm/@awesome.me/webawesome@3.2.1/dist-cdn/webawesome.loader.js"></script>
```

The loader auto-registers `wa-*` components as they appear in the DOM.

## Component Patterns

All tags are prefixed `wa-`. Attributes use kebab-case. Boolean attributes are present/absent (not `="true"`).

### Common Attributes

- `appearance`: `accent | filled | outlined | filled-outlined | plain`
- `variant`: `neutral | brand | success | warning | danger`
- `size`: `small | medium | large`
- `disabled`, `pill` (rounded)

### Components We Use

| Component | Docs |
|-----------|------|
| `wa-button` | https://webawesome.com/docs/components/button |
| `wa-input` | https://webawesome.com/docs/components/input |
| `wa-textarea` | https://webawesome.com/docs/components/textarea |
| `wa-select` + `wa-option` | https://webawesome.com/docs/components/select |
| `wa-switch` | https://webawesome.com/docs/components/switch |
| `wa-checkbox` | https://webawesome.com/docs/components/checkbox |
| `wa-card` | https://webawesome.com/docs/components/card |
| `wa-breadcrumb` | https://webawesome.com/docs/components/breadcrumb |
| `wa-callout` | https://webawesome.com/docs/components/callout |
| `wa-badge` | https://webawesome.com/docs/components/badge |
| `wa-icon` | https://webawesome.com/docs/components/icon |
| `wa-divider` | https://webawesome.com/docs/components/divider |
| `wa-progress-bar` | https://webawesome.com/docs/components/progress-bar |
| `wa-dialog` | https://webawesome.com/docs/components/dialog |
| `wa-tooltip` | https://webawesome.com/docs/components/tooltip |
| `wa-tag` | https://webawesome.com/docs/components/tag |
| `wa-dropdown` | https://webawesome.com/docs/components/dropdown |

### Quick Examples

```html
<!-- Buttons -->
<wa-button variant="brand">Primary</wa-button>
<wa-button appearance="outlined">Secondary</wa-button>
<wa-button variant="danger" appearance="outlined" size="small">Delete</wa-button>
<wa-button href="/path">Link button</wa-button>

<!-- Input with label (label is built-in) -->
<wa-input label="Name" name="name" placeholder="Enter name..." required></wa-input>
<wa-input type="number" label="Count" name="count"></wa-input>
<wa-input type="search" label="Search" name="q" with-clear></wa-input>

<!-- Textarea -->
<wa-textarea label="Notes" name="notes" rows="4" resize="vertical"></wa-textarea>

<!-- Select -->
<wa-select label="Status" name="status" placeholder="Choose...">
    <wa-option value="active">Active</wa-option>
    <wa-option value="inactive">Inactive</wa-option>
</wa-select>

<!-- Multiselect -->
<wa-select label="Tags" name="tags" multiple with-clear max-options-visible="3">
    <wa-option value="1" selected>Tag One</wa-option>
    <wa-option value="2">Tag Two</wa-option>
</wa-select>

<!-- Switch (boolean toggle) -->
<wa-switch name="enabled" checked>Enable feature</wa-switch>

<!-- Card with slots -->
<wa-card>
    <span slot="header">Title</span>
    Body content here.
    <wa-button slot="footer-actions" variant="brand">Save</wa-button>
</wa-card>

<!-- Breadcrumb -->
<wa-breadcrumb>
    <wa-breadcrumb-item href="/">Home</wa-breadcrumb-item>
    <wa-breadcrumb-item href="/items">Items</wa-breadcrumb-item>
    <wa-breadcrumb-item>Current</wa-breadcrumb-item>
</wa-breadcrumb>

<!-- Callout (alert) -->
<wa-callout variant="danger">Something went wrong.</wa-callout>
<wa-callout variant="success">Saved successfully.</wa-callout>

<!-- Icon (Font Awesome free icons bundled, 2000+) -->
<wa-icon name="gear"></wa-icon>
<wa-icon name="pen" variant="solid"></wa-icon>
<wa-icon family="brands" name="github"></wa-icon>

<!-- Progress bar -->
<wa-progress-bar value="65"></wa-progress-bar>
<wa-progress-bar indeterminate></wa-progress-bar>

<!-- Dialog (modal) -->
<wa-dialog label="Confirm" id="my-dialog">
    <p>Are you sure?</p>
    <wa-button slot="footer" data-dialog="close">Cancel</wa-button>
    <wa-button slot="footer" variant="brand" data-dialog="close">OK</wa-button>
</wa-dialog>
<wa-button data-dialog="open my-dialog">Open</wa-button>
```

## Theming

Built-in themes: `default.css`, `awesome.css`, `shoelace.css`.

Dark/light mode via CSS class on `<body>`:
```html
<body class="wa-light">  <!-- force light -->
<body class="wa-dark">   <!-- force dark -->
<!-- omit class = follow system preference -->
```

Override design tokens:
```css
:root {
    --wa-color-brand-600: #2563eb;
    --wa-font-sans: 'Inter', sans-serif;
}
```

Component-scoped properties (no `--wa-` prefix):
```css
wa-dialog { --width: 600px; }
wa-card { --spacing: 2rem; }
```

## Form Submission

All form controls (`wa-input`, `wa-select`, `wa-textarea`, `wa-switch`) participate in native `<form>` submission when they have a `name` attribute. `wa-select[multiple]` submits values accessible via `form_data.getlist(name)`.

## Styling Internals

Use `::part()` to style shadow DOM internals:
```css
wa-button::part(base) { border-radius: 0; }
wa-input::part(input) { font-family: monospace; }
```

## HTMX Compatibility

Web Awesome components work with HTMX. Place `hx-*` attributes on `wa-button` or wrapping elements. For HTMX-triggered requests from web components, regular DOM events (`click`, `submit`) propagate normally.

## Available Icons

Web Awesome bundles 2000+ Font Awesome free icons. Common ones:
`plus`, `pen`, `trash`, `magnifying-glass`, `gear`, `house`, `arrow-left`, `arrow-right`,
`circle-check`, `triangle-exclamation`, `circle-exclamation`, `spinner`, `ellipsis-vertical`,
`chevron-left`, `chevron-right`, `xmark`, `star`, `heart`, `eye`, `copy`, `download`.

Variant styles: `solid` (default), `regular`, `light`, `thin`.
