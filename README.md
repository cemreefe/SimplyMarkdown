# SimplyMarkdown

SimplyMarkdown turns one directory of Markdown into a complete static site. It is intentionally small: one build pipeline, one page model, and three explicit extension points.

## Install and build

Requires Python 3.11 or newer.

```bash
python -m pip install .
simplymarkdown \
  --input example/input \
  --output public \
  --root https://example.com \
  --title "Example Blog"
```

`--root` and `--title` are required because canonical URLs, RSS, and page titles cannot be generated correctly without them. The output directory is replaced transactionally: failed builds preserve the previous site, and removed source files cannot survive as stale output.

Run `simplymarkdown --help` for theme, template, favicon, preview, and RSS options. `python render.py` remains an equivalent compatibility entry point.

## Source layout

```text
source/
├── index.md
├── about.md
├── posts/
│   └── 2026/09/04/hello.md
├── modules/
│   ├── navbar.md
│   ├── footer.md
│   └── head_extras.html
└── static/
    └── images/
```

Markdown becomes HTML; other files are copied unchanged. `modules/` is private and files whose root-level name starts with `_` are ignored. A `.html` file containing `<convertsm>` is processed like Markdown-compatible HTML.

Modules are included on their own line:

```markdown
! include callout
```

`navbar`, `footer`, and `head_extras` are consumed by the bundled template. Unknown modules, duplicate names, include cycles, output collisions, invalid dates, and escaping paths fail the build with a useful error.

## Frontmatter

```markdown
---
title: A shorter metadata title
description: Used for search and social cards
emoji: 🛠️
date: 2026-09-04
tags: engineering
      static sites
image: ./cover.jpg
preview_shape: arch
language: en
featured: true
canonical_uri: articles/original
---

# The visible title
```

Dates are ISO `YYYY-MM-DD`. When omitted, a date is inferred from a `YYYY/MM/DD` source path; otherwise the page is left honestly undated. Git checkout times are never treated as publication dates.

`preview_shape` is optional theme metadata for detailed collections. Omit it (or use
`natural`) to preserve the image's native composition; use `arch` or `blob` to let a theme
apply an expressive crop. Detailed previews omit generated tables of contents,
`<parsers-ignore>` blocks, scripts, and styles.

## Collections

A collection line lists Markdown pages below a directory relative to the current page:

```markdown
% posts
% posts:detailed
% posts:featured
% posts:detailed:#engineering:#python
```

Modifiers compose: `detailed` renders excerpts, `featured` checks frontmatter, and every `#tag` must match. Collections are deterministically sorted newest-first.

## Templates and themes

Pass `--css path/to/theme.css` or `--template path/to/page.html`. Templates receive `context` with:

- `page`: the typed page model
- `content`: rendered page HTML
- `modules`: rendered modules by name
- `title`, `lang`, `root`, and `favicon_path`
- `meta_tags` and `category_tags`

Jinja autoescaping is enabled. Rendered Markdown and modules are the only values marked as trusted HTML.

## Extension API

The CLI stays opinionated; Python callers can add narrowly scoped behavior without replacing the build:

```python
from pathlib import Path, PurePosixPath
from simplymarkdown import BuildConfig, SiteBuilder


def replace_mark(context, page, source):
    return source.replace("{{ build-mark }}", "Built with care.")


def robots(context):
    return {PurePosixPath("robots.txt"): f"Sitemap: {context.root_url}/sitemap.xml\n"}


SiteBuilder(
    BuildConfig(Path("source"), Path("public"), "https://example.com", "My site"),
    markdown_transforms=(replace_mark,),
    artifact_generators=(robots,),
).build()
```

Transforms operate on discovered `Page` objects. Artifact generators consume the same completed page graph used by HTML, RSS, and sitemap generation—generated HTML is never parsed back into a second model.

## GitHub Pages

Copy [`workflow/render.yaml`](workflow/render.yaml) to `.github/workflows/render.yaml`, update the site URL and package ref, and enable GitHub Pages with **GitHub Actions** as its source. Pin SimplyMarkdown to a release or full commit SHA in production.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The implementation follows Python-Markdown's supported extension boundary and creates a fresh parser for each document, avoiding leaked parser state. See the [official extension API](https://python-markdown.github.io/extensions/api/).
