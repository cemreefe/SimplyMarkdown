# Changelog

All notable changes to SimplyMarkdown will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - Unreleased

### Added

- **New package structure**: Reorganized as a proper Python package (`simplymarkdown/`)
- **CLI with Click**: New command-line interface with subcommands
  - `simplymarkdown build` - Build the site
  - `simplymarkdown serve` - Start development server
  - `simplymarkdown init` - Initialize a new project
  - `simplymarkdown new` - Create a new blog post
- **Configuration file support**: YAML configuration via `simplymarkdown.yaml`
- **Watch mode**: Auto-rebuild on file changes with `--watch` flag
- **Development server**: Built-in HTTP server with `--serve` flag
- **Incremental builds**: Only rebuild changed files with `--incremental` flag
- **Draft support**: Mark posts as drafts with `draft: true` frontmatter
- **Search index generation**: JSON search index for client-side search
- **Related posts**: Show related posts based on tags
- **Pagination**: Paginate post listings with `% posts:paginate:10`
- **TOC module**: Table of contents via `! toc` tag
- **Type hints**: Full type annotations throughout codebase
- **Unit tests**: Comprehensive test suite with pytest
- **Integration tests**: End-to-end rendering tests
- **CI/CD pipeline**: GitHub Actions for testing and building

### Changed

- **Dependencies**: Updated and expanded requirements
  - Added: `click`, `pyyaml`, `watchdog` (optional)
  - All dependencies now have version constraints
- **Code quality**: 
  - Removed wildcard imports
  - Consistent snake_case naming
  - Added docstrings to all functions
- **File structure**: Moved to `simplymarkdown/` package directory
- **Configuration**: New `Config` dataclass with nested configs

### Fixed

- **File handle leak**: Fixed unclosed file in `render.py`
- **Extension parsing**: `get_extension()` now returns without leading dot
- **Debug statements**: Removed print statements from `generateSitemap.py`

### Deprecated

- Direct usage of `render.py` as script (use `simplymarkdown build` instead)

## [1.0.0] - 2023-07-03

### Added

- Initial release
- Markdown to HTML conversion
- Module system (navbar, footer, custom modules)
- Frontmatter support (title, date, tags, emoji, image)
- Special tags for post listings (`% directory`)
- Detailed preview mode (`% directory:detailed`)
- RSS feed generation
- Sitemap generation
- SEO meta tags (Open Graph, Twitter Cards)
- GitHub Pages integration workflow
- Syntax highlighting with Pygments
- Multiple theme support

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 2.0.0 | Unreleased | Package restructure, CLI, watch mode, tests |
| 1.0.0 | 2023-07-03 | Initial release |
