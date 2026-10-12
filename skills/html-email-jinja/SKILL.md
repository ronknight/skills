---
name: html-email-jinja
description: Build and render HTML marketing emails from Jinja2 templates that hold up in Gmail, Outlook, Apple Mail and dark mode - table layout, inline CSS, preheader, image and button rules, strict renders that fail on missing variables, cache-busted images, and draft-only sends. Use when creating or editing an email template, adding a template variable, mapping campaign copy into a template, or debugging an email that renders blank fields or breaks in a client.
license: MIT
---

# HTML email with Jinja

## Layout of a campaign

- Keep copy and layout apart: one folder per campaign holding `template.html`
  and a data file (`config.json` or YAML) with the subject, preheader, body
  copy and product rows.
- Shared header and footer go in partials (`{% include 'partials/header.html' %}`).
  Never paste copies into each template.
- If data keys and template variable names differ, do the mapping in **one**
  function. Adding a copy field means updating that function, or the template
  renders nothing for it. When you rename a key, translate the old name on load
  so old campaigns keep rendering.
- Prefer lists and loops (`{% for p in products %}`) over numbered variables
  (`Product1_Name`, `Product2_Name`, ...).

## Email HTML rules

Email clients are not browsers. These rules are not optional:

- An XHTML 1.0 Transitional (or HTML5) doctype, and table-based layout with
  `role="presentation"` on layout tables.
- Inline CSS for anything that must survive clients that strip or ignore
  `<style>`. Keep `<style>` for media queries and dark-mode overrides only.
- A 600px container, centred, fluid below that width. In Outlook, fix widths
  with `<!--[if mso]>` ghost tables.
- `<meta name="color-scheme" content="light dark">` and
  `<meta name="supported-color-schemes" content="light dark">`. Test in dark
  mode: transparent PNG logos on dark text disappear.
- A hidden preheader right after `<body>`. Otherwise clients show the first
  text they find.
- On every `<img>`: an absolute `https://` URL, explicit `width` (and `height`
  when known), meaningful `alt` (`alt=""` for spacers), and
  `style="display:block;border:0"`.
- Bulletproof buttons: put the padding and background on the `<td>`, not the
  `<a>`, because Outlook ignores padding on links.
- No JavaScript, no forms, no CSS background images without a VML fallback.
- Keep the HTML under about 100 KB. Gmail clips longer messages and hides the
  rest, including the footer and unsubscribe link.

See [references/skeleton.html](references/skeleton.html) for a minimal
starting point.

## Rendering

Render strictly, so a missing variable fails loudly instead of rendering as an
empty string:

```python
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    undefined=StrictUndefined,
    autoescape=select_autoescape(["html"]),
)
html = env.get_template("campaigns/spring-sale/template.html").render(**data, cache_buster=run_stamp)
```

- **Autoescape on.** Mark trusted rich-text copy with `|safe` deliberately, and
  never mark user-supplied values that way.
- **Templates are code.** Render only templates from the repo. Never turn
  user-supplied or fetched text into a template (`Template(text)`,
  `env.from_string(text)`), because that allows server-side template injection.
  If other people must supply templates, render them in
  `jinja2.sandbox.SandboxedEnvironment`.
- **Cache-busting.** Append `?v={{ cache_buster }}` (a render timestamp) to
  images you overwrite in place on a CDN, so a re-send doesn't serve a stale
  asset.
- **ESP merge tags can clash with Jinja.** Some platforms use `{{ ... }}` and
  `{% ... %}` themselves. Wrap their tags in `{% raw %}...{% endraw %}`, or
  change Jinja's delimiters. Tags like `*|FNAME|*` don't conflict.
- Write output to a timestamped file such as `output/<campaign>_<YYYYmmdd_HHMMSS>.html`.

## Check before calling it done

Run the linter on the rendered file:

```bash
python scripts/lint_email.py output/spring-sale_20261012_101500.html
```

It flags leftover template syntax, images without `alt`, `width` or an `https`
URL, empty or non-https links, a missing doctype or color-scheme meta,
`<script>` and `<form>` tags, and size over the Gmail clipping limit. It uses
only the standard library.

Then open the file and read it: check the subject and preheader, that every
product row has a name, price, link and image, and that links point where the
copy says they do.

## Sending

Never send a live campaign from automation. Create a **draft** in the email
platform and hand it to a person. Test sends go to an internal seed list, and
only with explicit approval.

Read the platform's API key from an environment variable. Never put it in a
template, a data file or the rendered output.
