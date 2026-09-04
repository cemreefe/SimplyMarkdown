from __future__ import annotations

import fnmatch
import html
import posixpath
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from email.utils import format_datetime
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Protocol, cast
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4
from xml.etree import ElementTree as ET

import markdown
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, select_autoescape
from markdown.extensions.codehilite import CodeHiliteExtension
from markupsafe import Markup


class BuildError(RuntimeError):
    """An actionable site-build failure."""


@dataclass(frozen=True, slots=True)
class BuildConfig:
    input_dir: Path
    output_dir: Path
    root_url: str
    title: str
    css: Path | None = None
    template: Path | None = None
    favicon: str = "👤"
    rss_whitelist: tuple[str, ...] = ("*",)
    rss_description: str = "This is an RSS feed of my website."
    preview_limit: int = 6


@dataclass(frozen=True, slots=True)
class FrontMatter:
    values: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: MappingProxyType({}))

    def one(self, key: str, default: str | None = None) -> str | None:
        values = self.values.get(key.lower())
        return values[0] if values else default

    def many(self, key: str) -> tuple[str, ...]:
        return self.values.get(key.lower(), ())


@dataclass(slots=True)
class Page:
    source: Path
    source_rel: PurePosixPath
    output_rel: PurePosixPath
    url_path: str
    body: str
    meta: FrontMatter
    title: str
    published: date | None
    tags: tuple[str, ...]
    emoji: str
    featured: bool
    base_html: str = ""
    content_html: str = ""
    description: str = ""
    canonical_url: str = ""

    @property
    def language(self) -> str:
        return self.meta.one("language", "en") or "en"


@dataclass(slots=True)
class BuildContext:
    config: BuildConfig
    root_url: str
    origin: str
    base_path: str
    pages: list[Page]
    modules: dict[str, str]
    by_source: dict[str, Page]
    by_output: dict[str, Page]
    by_url: dict[str, Page]


@dataclass(frozen=True, slots=True)
class BuildResult:
    output_dir: Path
    pages: tuple[Page, ...]


MarkdownTransform = Callable[[BuildContext, Page, str], str]
HtmlTransform = Callable[[BuildContext, Page, str], str]
Artifact = str | bytes


class ArtifactGenerator(Protocol):
    def __call__(self, context: BuildContext) -> Mapping[PurePosixPath, Artifact]: ...


@dataclass(frozen=True, slots=True)
class _Module:
    name: str
    path: Path
    body: str
    is_html: bool


class SiteBuilder:
    """A deterministic, transactional static-site build pipeline."""

    _INCLUDE = re.compile(
        r"^[ \t]*![ \t]+include[ \t]+(?P<name>[^\n]+?)[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )
    _COLLECTION = re.compile(r"^[ \t]*%[ \t]+(?P<spec>[^\n]+?)[ \t]*$", re.MULTILINE)
    _PACKAGE_DIR = Path(__file__).resolve().parent

    def __init__(
        self,
        config: BuildConfig,
        *,
        markdown_transforms: tuple[MarkdownTransform, ...] = (),
        html_transforms: tuple[HtmlTransform, ...] = (),
        artifact_generators: tuple[ArtifactGenerator, ...] = (),
    ) -> None:
        self.config = config
        self.markdown_transforms = markdown_transforms
        self.html_transforms = html_transforms
        self.artifact_generators = artifact_generators

    def build(self) -> BuildResult:
        config, root_url, origin, base_path = self._validated_config()
        pages, assets, module_sources = self._discover(config)
        context = BuildContext(
            config=config,
            root_url=root_url,
            origin=origin,
            base_path=base_path,
            pages=pages,
            modules={},
            by_source={page.source_rel.as_posix(): page for page in pages},
            by_output={page.output_rel.as_posix(): page for page in pages},
            by_url={page.url_path.rstrip("/"): page for page in pages},
        )
        context.modules.update(self._render_modules(module_sources))

        for page in pages:
            source = self._expand_includes(context, page, page.body)
            source = self._COLLECTION.sub("", source)
            page.base_html = self._render_content(context, page, source)

        for page in pages:
            source = self._expand_includes(context, page, page.body)
            page.content_html = (
                self._render_content(context, page, self._expand_collections(context, page, source))
                if self._COLLECTION.search(source)
                else page.base_html
            )
            page.description = page.meta.one("description") or self._description(page.content_html)
            page.canonical_url = self._canonical_url(context, page)

        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{config.output_dir.name}.build-",
                dir=config.output_dir.parent,
            )
        )
        try:
            self._write_site(context, staging, assets)
            self._commit(staging, config.output_dir)
        except TemplateError as error:
            shutil.rmtree(staging, ignore_errors=True)
            raise BuildError(f"template rendering failed: {error}") from error
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return BuildResult(config.output_dir, tuple(pages))

    def _validated_config(self) -> tuple[BuildConfig, str, str, str]:
        source = self.config.input_dir.expanduser().resolve()
        output_arg = self.config.output_dir.expanduser()
        if output_arg.is_symlink():
            raise BuildError(f"output directory may not be a symlink: {output_arg}")
        output = output_arg.resolve()
        if not source.is_dir():
            raise BuildError(f"input directory does not exist: {source}")
        if output.exists() and not output.is_dir():
            raise BuildError(f"output path is not a directory: {output}")
        if source == output or source.is_relative_to(output) or output.is_relative_to(source):
            raise BuildError("input and output directories must not overlap")
        if not self.config.title.strip():
            raise BuildError("site title must not be empty")
        if self.config.preview_limit < 1:
            raise BuildError("preview limit must be at least 1")

        parsed = urlsplit(self.config.root_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise BuildError("root URL must be an absolute http(s) URL")
        if parsed.query or parsed.fragment:
            raise BuildError("root URL must not contain a query or fragment")
        base_path = parsed.path.rstrip("/")
        root_url = urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))

        css = (self.config.css or self._PACKAGE_DIR / "basic.css").expanduser().resolve()
        template = (self.config.template or self._PACKAGE_DIR / "base.html").expanduser().resolve()
        for label, path in (("CSS", css), ("template", template)):
            if not path.is_file():
                raise BuildError(f"{label} file does not exist: {path}")
        output.parent.mkdir(parents=True, exist_ok=True)
        config = BuildConfig(
            input_dir=source,
            output_dir=output,
            root_url=root_url,
            title=self.config.title.strip(),
            css=css,
            template=template,
            favicon=self.config.favicon,
            rss_whitelist=tuple(p.strip() for p in self.config.rss_whitelist if p.strip())
            or ("*",),
            rss_description=self.config.rss_description,
            preview_limit=self.config.preview_limit,
        )
        return config, root_url, origin, base_path

    def _discover(
        self, config: BuildConfig
    ) -> tuple[list[Page], list[tuple[Path, PurePosixPath]], list[_Module]]:
        pages: list[Page] = []
        assets: list[tuple[Path, PurePosixPath]] = []
        modules: list[_Module] = []
        outputs: dict[str, Path] = {}
        module_names: dict[str, Path] = {}

        for path in sorted(config.input_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = PurePosixPath(path.relative_to(config.input_dir).as_posix())
            if rel.parts[0] == "modules":
                if path.suffix.lower() not in {".md", ".html"}:
                    continue
                name = path.stem
                if name in module_names:
                    raise BuildError(
                        f"duplicate module name {name!r}: {module_names[name]} and {path}"
                    )
                module_names[name] = path
                modules.append(
                    _Module(name, path, self._read(path), path.suffix.lower() == ".html")
                )
                continue
            if rel.parts[0].startswith("_"):
                continue

            is_markdown = path.suffix.lower() == ".md"
            text = self._read(path) if is_markdown or path.suffix.lower() == ".html" else ""
            is_convertible_html = path.suffix.lower() == ".html" and "<convertsm>" in text.lower()
            if not is_markdown and not is_convertible_html:
                assets.append((path, rel))
                self._claim_output(outputs, rel, path)
                continue

            body_source = re.sub(r"<convertsm>\s*", "", text, flags=re.IGNORECASE)
            meta, body = self._frontmatter(body_source, path)
            output_name = self._slug(path.stem) + ".html"
            output_rel = rel.with_name(output_name)
            self._claim_output(outputs, output_rel, path)
            url_path = output_rel.with_suffix("").as_posix()
            if output_rel.stem.lower() == "index":
                parent = output_rel.parent.as_posix()
                url_path = "" if parent == "." else parent.rstrip("/") + "/"
            published = self._published(meta, rel, path)
            tags = tuple(
                tag
                for value in meta.many("tags")
                for tag in (part.strip() for part in value.split(","))
                if tag
            )
            title = meta.one("title") or self._inferred_title(body) or path.stem
            featured = (meta.one("featured", "false") or "false").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            pages.append(
                Page(
                    source=path,
                    source_rel=rel,
                    output_rel=output_rel,
                    url_path=url_path,
                    body=body,
                    meta=meta,
                    title=title,
                    published=published,
                    tags=tags,
                    emoji=meta.one("emoji", "⏩") or "⏩",
                    featured=featured,
                )
            )
        if not pages:
            raise BuildError(f"no Markdown pages found in {config.input_dir}")
        return pages, assets, modules

    @staticmethod
    def _claim_output(outputs: dict[str, Path], rel: PurePosixPath, source: Path) -> None:
        key = rel.as_posix().casefold()
        if previous := outputs.get(key):
            raise BuildError(f"output collision: {previous} and {source} both produce {rel}")
        outputs[key] = source

    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeError as error:
            raise BuildError(f"expected UTF-8 text in {path}") from error

    @staticmethod
    def _slug(stem: str) -> str:
        slug = re.sub(r",\s+|\s+", "-", stem.strip())
        if not slug or slug in {".", ".."}:
            raise BuildError(f"cannot create a URL from filename {stem!r}")
        return slug

    @staticmethod
    def _frontmatter(text: str, path: Path) -> tuple[FrontMatter, str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return FrontMatter(), text
        try:
            end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
        except StopIteration as error:
            raise BuildError(f"unterminated frontmatter in {path}") from error

        values: dict[str, list[str]] = {}
        current: str | None = None
        for number, line in enumerate(lines[1:end], 2):
            if not line.strip():
                continue
            if line[:1].isspace():
                if current is None:
                    raise BuildError(f"invalid frontmatter at {path}:{number}")
                value = line.strip()
                values[current].append(value[2:].strip() if value.startswith("- ") else value)
                continue
            if ":" not in line:
                raise BuildError(f"invalid frontmatter at {path}:{number}")
            key, value = line.split(":", 1)
            current = key.strip().lower()
            if not current:
                raise BuildError(f"empty frontmatter key at {path}:{number}")
            values.setdefault(current, [])
            if value.strip():
                values[current].append(value.strip())
        frozen = MappingProxyType({key: tuple(items) for key, items in values.items()})
        body = "\n".join(lines[end + 1 :]).lstrip("\n")
        return FrontMatter(frozen), body

    @staticmethod
    def _published(meta: FrontMatter, rel: PurePosixPath, source: Path) -> date | None:
        value = meta.one("date")
        if value:
            try:
                return date.fromisoformat(value)
            except ValueError as error:
                raise BuildError(f"invalid ISO date {value!r} in {source}") from error
        parts = rel.parts[:-1]
        for index in range(len(parts) - 2):
            candidate = "-".join(parts[index : index + 3])
            try:
                return date.fromisoformat(candidate)
            except ValueError:
                pass
        return None

    def _inferred_title(self, body: str) -> str:
        source = self._COLLECTION.sub("", self._INCLUDE.sub("", body))
        soup = BeautifulSoup(self._markdown(source), "html.parser")
        element = soup.find(re.compile(r"^h[1-6]$")) or soup.find("p")
        return element.get_text(" ", strip=True) if element else ""

    @staticmethod
    def _markdown(source: str) -> str:
        renderer = markdown.Markdown(
            extensions=[
                "extra",
                "toc",
                CodeHiliteExtension(noclasses=True, pygments_style="colorful"),
            ],
            output_format="html",
        )
        return renderer.convert(source)

    def _render_modules(self, sources: list[_Module]) -> dict[str, str]:
        by_name = {module.name: module for module in sources}
        rendered: dict[str, str] = {}

        def render(name: str, stack: tuple[str, ...] = ()) -> str:
            if name in rendered:
                return rendered[name]
            if name in stack:
                raise BuildError(f"module include cycle: {' -> '.join((*stack, name))}")
            module = by_name.get(name)
            if module is None:
                raise BuildError(f"unknown module {name!r}")

            def replace(match: re.Match[str]) -> str:
                return render(match.group("name").strip(), (*stack, name))

            body = self._INCLUDE.sub(replace, module.body)
            body = self._COLLECTION.sub("", body)
            rendered[name] = body if module.is_html else self._markdown(body)
            return rendered[name]

        for name in by_name:
            render(name)
        return rendered

    def _expand_includes(self, context: BuildContext, page: Page, source: str) -> str:
        def replace(match: re.Match[str]) -> str:
            name = match.group("name").strip()
            try:
                return context.modules[name]
            except KeyError as error:
                raise BuildError(f"unknown module {name!r} included by {page.source}") from error

        return self._INCLUDE.sub(replace, source)

    def _render_content(self, context: BuildContext, page: Page, source: str) -> str:
        for transform in self.markdown_transforms:
            source = transform(context, page, source)
        rendered = self._markdown(source)
        for transform in self.html_transforms:
            rendered = transform(context, page, rendered)
        return self._rewrite_urls(context, page, rendered)

    def _expand_collections(self, context: BuildContext, page: Page, source: str) -> str:
        def replace(match: re.Match[str]) -> str:
            spec = match.group("spec").strip()
            directory, *modifiers = (part.strip() for part in spec.split(":"))
            detailed = "detailed" in modifiers
            featured = "featured" in modifiers
            tags = {part[1:] for part in modifiers if part.startswith("#") and len(part) > 1}
            unknown = [
                part
                for part in modifiers
                if part not in {"detailed", "featured"} and not part.startswith("#")
            ]
            if unknown:
                raise BuildError(f"unknown collection modifier {unknown[0]!r} in {page.source}")
            if not directory:
                raise BuildError(f"collection directory is empty in {page.source}")
            collection_dir = (page.source.parent / directory).resolve()
            if not collection_dir.is_relative_to(context.config.input_dir):
                raise BuildError(
                    f"collection escapes the input directory in {page.source}: {directory}"
                )
            if not collection_dir.is_dir():
                raise BuildError(f"collection directory does not exist: {collection_dir}")
            items = [item for item in context.pages if item.source.is_relative_to(collection_dir)]
            if featured:
                items = [item for item in items if item.featured]
            if tags:
                items = [item for item in items if tags.issubset(set(item.tags))]
            items.sort(key=lambda item: item.url_path)
            items.sort(key=lambda item: item.published or date.min, reverse=True)
            return self._collection_html(context, items, detailed)

        return self._COLLECTION.sub(replace, source)

    def _collection_html(self, context: BuildContext, pages: list[Page], detailed: bool) -> str:
        parts = ['<div class="postsListWrapper">']
        previous_year: str | None = None
        for page in pages:
            href = html.escape(self._public_path(context, page.url_path), quote=True)
            tags = html.escape(",".join(page.tags), quote=True)
            if detailed:
                preview_shape = (page.meta.one("preview_shape", "natural") or "natural").lower()
                if preview_shape not in {"natural", "arch", "blob"}:
                    raise BuildError(
                        f"invalid preview_shape {preview_shape!r} in {page.source}; "
                        "expected natural, arch, or blob"
                    )
                shape_class = (
                    f" postPreview--{preview_shape}" if preview_shape != "natural" else ""
                )
                date_markup = (
                    f'<div class="previewDate">{page.published.isoformat()}</div>'
                    if page.published
                    else ""
                )
                preview, truncated = self._preview(page.base_html, context.config.preview_limit)
                more = '<span class="readMore">(Read more)</span>' if truncated else ""
                parts.append(
                    f'<article class="postPreview{shape_class}" data-tags="{tags}">{date_markup}'
                    f'<a class="previewHref" href="{href}"><div>{preview}</div>{more}</a></article>'
                )
                continue
            year = str(page.published.year) if page.published else "Undated"
            if year != previous_year:
                parts.append(f'<div class="dateTab">{year}</div>')
                previous_year = year
            label = html.escape(f"{page.emoji} {page.title}")
            parts.append(
                f'<div class="postTitle" data-tags="{tags}"><a href="{href}">{label}</a></div>'
            )
        parts.append("</div>")
        return "\n".join(parts)

    @staticmethod
    def _preview(rendered: str, limit: int) -> tuple[str, bool]:
        soup = BeautifulSoup(rendered, "html.parser")
        for excluded in soup.select(".toc, parsers-ignore, script, style"):
            excluded.decompose()
        for paragraph in soup.find_all("p"):
            if not paragraph.get_text(strip=True) and not paragraph.find(
                ("audio", "iframe", "img", "picture", "svg", "video")
            ):
                paragraph.decompose()
        for link in soup.find_all("a"):
            link.unwrap()
        nodes = [node for node in soup.contents if str(node).strip()]
        truncated = len(nodes) > limit
        fragment = BeautifulSoup("".join(str(node) for node in nodes[:limit]), "html.parser")
        if heading := fragment.find("h1"):
            heading.name = "h2"
            heading["class"] = "preview-title"
        return str(fragment), truncated

    def _rewrite_urls(self, context: BuildContext, page: Page, rendered: str) -> str:
        soup = BeautifulSoup(rendered, "html.parser")
        for tag in soup.find_all(True):
            for attribute in ("href", "src", "poster"):
                value = tag.get(attribute)
                if isinstance(value, str):
                    tag[attribute] = self._resolve_reference(
                        context, page, value, attribute == "href"
                    )
            srcset = tag.get("srcset")
            if isinstance(srcset, str):
                candidates = []
                for candidate in srcset.split(","):
                    url, *descriptor = candidate.strip().split()
                    resolved = self._resolve_reference(context, page, url, False)
                    candidates.append(" ".join((resolved, *descriptor)))
                tag["srcset"] = ", ".join(candidates)
        return str(soup)

    def _resolve_reference(
        self, context: BuildContext, page: Page, value: str, is_link: bool
    ) -> str:
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or value.startswith(("#", "//")) or not parsed.path:
            return value
        if context.base_path and (
            parsed.path == context.base_path or parsed.path.startswith(context.base_path + "/")
        ):
            return value

        raw = parsed.path.lstrip("/")
        base = "" if parsed.path.startswith("/") else page.source_rel.parent.as_posix()
        target = posixpath.normpath(posixpath.join(base, raw))
        if target == ".":
            target = ""
        if target == ".." or target.startswith("../"):
            raise BuildError(f"local URL escapes the site in {page.source}: {value}")

        destination = target
        if is_link:
            linked_page = (
                context.by_source.get(target)
                or context.by_output.get(target)
                or context.by_url.get(target.rstrip("/"))
            )
            if linked_page:
                destination = linked_page.url_path
            elif PurePosixPath(target).suffix.lower() == ".md":
                raise BuildError(
                    f"link points to an unknown Markdown page in {page.source}: {value}"
                )
        path = self._public_path(context, destination)
        return urlunsplit(("", "", path, parsed.query, parsed.fragment))

    @staticmethod
    def _absolute_html(context: BuildContext, rendered: str) -> str:
        soup = BeautifulSoup(rendered, "html.parser")
        for unsafe in soup.find_all(("script", "style", "parsers-ignore")):
            unsafe.decompose()
        for tag in soup.find_all(True):
            tag.attrs = {
                name: value
                for name, value in tag.attrs.items()
                if name != "style" and not name.lower().startswith("on")
            }
            for attribute in ("href", "src", "poster"):
                value = tag.get(attribute)
                if isinstance(value, str) and value.startswith("/") and not value.startswith("//"):
                    tag[attribute] = context.origin + value
            srcset = tag.get("srcset")
            if isinstance(srcset, str):
                tag["srcset"] = ", ".join(
                    " ".join(
                        (
                            context.origin + parts[0]
                            if parts[0].startswith("/") and not parts[0].startswith("//")
                            else parts[0],
                            *parts[1:],
                        )
                    )
                    for candidate in srcset.split(",")
                    if (parts := candidate.strip().split())
                )
        return str(soup)

    @staticmethod
    def _quoted_path(path: str) -> str:
        return "/".join(quote(part, safe="!$&'()*+,;=:@%~-._") for part in path.split("/"))

    def _public_path(self, context: BuildContext, path: str) -> str:
        quoted = self._quoted_path(path.lstrip("/"))
        result = f"{context.base_path}/{quoted}" if quoted else f"{context.base_path}/"
        return result if result.startswith("/") else "/" + result

    def _absolute_path(self, context: BuildContext, path: str) -> str:
        return context.origin + self._public_path(context, path)

    def _canonical_url(self, context: BuildContext, page: Page) -> str:
        override = page.meta.one("canonical_uri")
        if not override:
            return self._absolute_path(context, page.url_path)
        parsed = urlsplit(override)
        if parsed.scheme:
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise BuildError(f"invalid canonical URL in {page.source}: {override}")
            return override
        return self._absolute_path(context, override.lstrip("/"))

    @staticmethod
    def _description(rendered: str, limit: int = 160) -> str:
        soup = BeautifulSoup(rendered, "html.parser")
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(part for part in paragraphs if part)
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    def _meta_image(self, context: BuildContext, page: Page) -> str:
        image = page.meta.one("image")
        if not image:
            return self._absolute_path(context, "static/img/default_img.png")
        parsed = urlsplit(image)
        if parsed.scheme or parsed.netloc:
            return image
        raw = parsed.path.lstrip("/")
        base = "" if parsed.path.startswith("/") else page.source_rel.parent.as_posix()
        path = posixpath.normpath(posixpath.join(base, raw))
        return self._absolute_path(context, path)

    def _meta_tags(self, context: BuildContext, page: Page) -> Markup:
        image = self._meta_image(context, page)

        def meta(name: str, value: str, *, prop: bool = False) -> Markup:
            attribute = "property" if prop else "name"
            return Markup('<meta {}="{}" content="{}">').format(attribute, name, value)

        tags = [
            meta("description", page.description),
            meta("og:title", page.title, prop=True),
            meta("og:image", image, prop=True),
            meta("og:description", page.description, prop=True),
            meta("og:type", "article" if page.published else "website", prop=True),
            meta("og:url", page.canonical_url, prop=True),
            meta("twitter:card", "summary_large_image"),
            meta("twitter:title", page.title),
            meta("twitter:description", page.description),
            meta("twitter:image", image),
            Markup('<link rel="canonical" href="{}">').format(page.canonical_url),
        ]
        if page.published:
            tags.append(meta("article:published_time", page.published.isoformat(), prop=True))
            tags.append(meta("pubdate", self._rfc_date(page.published)))
        return Markup("\n").join(tags)

    def _write_site(
        self,
        context: BuildContext,
        staging: Path,
        assets: list[tuple[Path, PurePosixPath]],
    ) -> None:
        for source, rel in assets:
            destination = staging.joinpath(*rel.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        css_destination = staging / "static/css/theme.css"
        css_destination.parent.mkdir(parents=True, exist_ok=True)
        css = cast(Path, context.config.css)
        template_path = cast(Path, context.config.template)
        shutil.copy2(css, css_destination)

        environment = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=select_autoescape(("html", "xml"), default=True),
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )
        template = environment.get_template(template_path.name)
        for page in context.pages:
            modules = {
                name: Markup(self._rewrite_urls(context, page, value))
                for name, value in context.modules.items()
            }
            document_title = (
                page.title
                if page.title.casefold() == context.config.title.casefold()
                else f"{page.title} · {context.config.title}"
            )
            template_context = {
                "lang": page.language,
                "root": context.root_url,
                "favicon_path": f"https://emoji.dutl.uk/png/64x64/{quote(context.config.favicon)}.png",
                "title": document_title,
                "page": page,
                "modules": modules,
                "content": Markup(page.content_html),
                "meta_tags": self._meta_tags(context, page),
                "category_tags": page.tags,
            }
            output = template.render(context=template_context)
            destination = staging.joinpath(*page.output_rel.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(output, encoding="utf-8")

        generators: tuple[ArtifactGenerator, ...] = (
            self._sitemap,
            self._rss,
            *self.artifact_generators,
        )
        claimed = {page.output_rel.as_posix().casefold() for page in context.pages}
        claimed.update(rel.as_posix().casefold() for _, rel in assets)
        claimed.add("static/css/theme.css")
        for generator in generators:
            for rel, content in generator(context).items():
                if rel.is_absolute() or ".." in rel.parts:
                    raise BuildError(f"artifact path escapes output directory: {rel}")
                key = rel.as_posix().casefold()
                if key in claimed:
                    raise BuildError(f"artifact output collision: {rel}")
                claimed.add(key)
                destination = staging.joinpath(*rel.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    destination.write_bytes(content)
                else:
                    destination.write_text(content, encoding="utf-8")

    def _sitemap(self, context: BuildContext) -> Mapping[PurePosixPath, Artifact]:
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        ET.register_namespace("", namespace)
        root = ET.Element(f"{{{namespace}}}urlset")
        for page in context.pages:
            if urlsplit(page.canonical_url).netloc != urlsplit(context.root_url).netloc:
                continue
            url = ET.SubElement(root, f"{{{namespace}}}url")
            ET.SubElement(url, f"{{{namespace}}}loc").text = page.canonical_url
        return {PurePosixPath("sitemap.xml"): self._xml(root)}

    def _rss(self, context: BuildContext) -> Mapping[PurePosixPath, Artifact]:
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = context.config.title
        ET.SubElement(channel, "link").text = context.root_url + "/"
        ET.SubElement(channel, "description").text = context.config.rss_description
        pages = [page for page in context.pages if self._rss_includes(context, page)]
        pages.sort(key=lambda page: page.url_path)
        pages.sort(key=lambda page: page.published or date.min, reverse=True)
        for page in pages:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = page.title
            ET.SubElement(item, "link").text = page.canonical_url
            ET.SubElement(item, "guid", isPermaLink="true").text = page.canonical_url
            if page.published:
                ET.SubElement(item, "pubDate").text = self._rfc_date(page.published)
            content = self._absolute_html(context, page.content_html)
            ET.SubElement(item, "description").text = f"<main>{content}</main>"
            for tag in page.tags:
                ET.SubElement(item, "category").text = tag
        return {PurePosixPath("rss.xml"): self._xml(rss)}

    @staticmethod
    def _rss_includes(context: BuildContext, page: Page) -> bool:
        candidates = {
            page.url_path,
            "/" + page.url_path,
            page.output_rel.as_posix(),
            "/" + page.output_rel.as_posix(),
        }
        return any(
            fnmatch.fnmatch(candidate, pattern)
            for pattern in context.config.rss_whitelist
            for candidate in candidates
        )

    @staticmethod
    def _rfc_date(value: date) -> str:
        return format_datetime(datetime.combine(value, time.min, tzinfo=UTC), usegmt=True)

    @staticmethod
    def _xml(root: ET.Element) -> bytes:
        ET.indent(root, space="  ")
        return cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=True))

    @staticmethod
    def _commit(staging: Path, output: Path) -> None:
        backup = output.with_name(f".{output.name}.previous-{uuid4().hex}")
        had_output = output.exists()
        try:
            if had_output:
                output.rename(backup)
            staging.rename(output)
        except Exception:
            if had_output and backup.exists() and not output.exists():
                backup.rename(output)
            raise
        finally:
            if backup.exists() and output.exists():
                shutil.rmtree(backup)
