# SimplyMarkdown

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SimplyMarkdown** is a lightweight static site generator that transforms your Markdown files into a beautiful, fully-functional website. No complex configurations, no bloated features—just simple, effective content management.

## ✨ Features

- 🚀 **Simple & Fast** — Convert Markdown to HTML with minimal configuration
- 📝 **Module System** — Reusable components for navbar, footer, and custom modules
- 🏷️ **Frontmatter Support** — Rich metadata with title, date, tags, and more
- 📰 **Auto-generated Feeds** — RSS and sitemap out of the box
- 🔍 **Search Index** — JSON search index for client-side search
- 🎨 **Syntax Highlighting** — Beautiful code blocks with Pygments
- 👀 **Watch Mode** — Auto-rebuild on file changes
- 🌐 **Dev Server** — Built-in development server
- 📦 **Incremental Builds** — Only rebuild changed files

## 📦 Installation

Clone the repository and install locally:

```bash
git clone https://github.com/cemreefe/SimplyMarkdown.git
cd SimplyMarkdown
pip install -e .
```

Or install with development dependencies:

```bash
pip install -e ".[all]"
```

## 🚀 Quick Start

### Initialize a New Project

```bash
simplymarkdown init my-blog
cd my-blog
simplymarkdown build -i source -o output --serve
```

### Or Start from Scratch

1. Create your content structure:

```
my-site/
├── source/
│   ├── index.md
│   ├── about.md
│   ├── posts/
│   │   └── 2024/01/15/my-first-post.md
│   ├── modules/
│   │   ├── navbar.md
│   │   └── footer.md
│   └── static/
│       └── img/
└── output/
```

2. Build your site:

```bash
simplymarkdown build -i source -o output
```

3. Start the development server with auto-rebuild:

```bash
simplymarkdown build -i source -o output --serve --watch
```

## 📖 Usage

### CLI Commands

```bash
# Build the site
simplymarkdown build -i source -o output

# Build with all options
simplymarkdown build \
  -i source \
  -o output \
  --title "My Blog" \
  --root https://myblog.com \
  --favicon 🚀 \
  --serve \
  --watch

# Start development server only
simplymarkdown serve output

# Initialize a new project
simplymarkdown init my-project

# Create a new blog post
simplymarkdown new "My New Post"
```

### Configuration File

Create `simplymarkdown.yaml` in your project root:

```yaml
input: source
output: output
title: My Blog
root: https://myblog.com
favicon: 🚀

template: templates/base.html
theme: themes/custom.css

rss:
  whitelist: "/posts/*"
  description: "My blog's RSS feed"

build:
  include_drafts: false
  incremental: true

server:
  port: 8000
  open_browser: true
```

## ✍️ Writing Content

### Frontmatter

Every Markdown file can have YAML frontmatter:

```markdown
---
title: My Awesome Post
date: 2024-01-15
emoji: 🎉
tags: python
      web
      tutorial
image: /static/img/cover.png
description: A brief description for SEO
language: en
draft: false
---

# My Awesome Post

Your content here...
```

### Available Frontmatter Fields

| Field | Description | Default |
|-------|-------------|---------|
| `title` | Page/post title | First heading |
| `date` | Publication date (YYYY-MM-DD) | File modification date |
| `emoji` | Emoji shown in listings | ⏩ |
| `tags` | Category tags (one per line) | None |
| `image` | Open Graph image | `/static/img/default_img.png` |
| `description` | Meta description | First paragraph |
| `language` | Page language | `en` |
| `draft` | If `true`, excluded from build | `false` |
| `canonical_uri` | Override canonical URL | Auto-generated |
| `show_related` | Show related posts | `false` |
| `related_count` | Number of related posts | 5 |

## 🧩 Modules

### Built-in Modules

Place these files in `source/modules/`:

- **`navbar.md`** — Navigation bar (included on all pages)
- **`footer.md`** — Footer content (included on all pages)
- **`head_extras.html`** — Extra content for `<head>` (analytics, fonts, etc.)

### Custom Modules

Create any `.md` file in `modules/` and include it:

```markdown
! include my-custom-module
```

This includes `modules/my-custom-module.md` at that location.

## 📋 Special Tags

### Post Listings

List all posts in a directory:

```markdown
% posts
```

Detailed listings with previews:

```markdown
% posts:detailed
```

With pagination:

```markdown
% posts:paginate:10
```

### Table of Contents

Generate a table of contents from headings:

```markdown
! toc
```

With max heading level:

```markdown
! toc:maxlevel:3
```

## 🎨 Themes

### Using a Theme

```bash
simplymarkdown build -i source -o output --css themes/custom.css
```

### Creating a Theme

Create a CSS file with styles for:

```css
/* Base styles */
body { ... }

/* Navigation */
nav { ... }

/* Content */
main { ... }
.content { ... }

/* Post listings */
.postsListWrapper { ... }
.postTitle { ... }
.postPreview { ... }
.dateTab { ... }

/* Category tags */
categoryTag { ... }

/* Code highlighting */
.highlight { ... }

/* Footer */
footer { ... }
```

## 🌐 GitHub Pages Deployment

### Automatic Deployment

Add this workflow to `.github/workflows/deploy.yaml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install SimplyMarkdown
        run: |
          git clone https://github.com/cemreefe/SimplyMarkdown.git
          pip install ./SimplyMarkdown
      
      - name: Build site
        run: |
          simplymarkdown build \
            -i source \
            -o output \
            --title "My Blog" \
            --root "https://username.github.io"
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output
```

## 📁 Project Structure

After building, your output will look like:

```
output/
├── index.html
├── about.html
├── posts/
│   └── 2024/01/15/my-first-post.html
├── static/
│   ├── css/
│   │   └── theme.css
│   └── img/
├── sitemap.xml
├── rss.xml
└── search-index.json
```

## 🔧 Development

### Setup

```bash
git clone https://github.com/cemreefe/SimplyMarkdown.git
cd SimplyMarkdown
pip install -e ".[all]"
```

### Running Tests

```bash
pytest
pytest --cov=simplymarkdown
```

### Linting

```bash
ruff check simplymarkdown tests
mypy simplymarkdown
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

Made with ❤️ by [cemreefe](https://github.com/cemreefe)
