"""Configuration constants and settings for SimplyMarkdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Directory names
MODULES_DIR = "modules"

# File patterns
MARKDOWN_EXTENSIONS = (".md", ".markdown")
HTML_EXTENSION = ".html"
CONVERT_TAG = "<convertsm>"

# Default values
DEFAULT_FAVICON = "👤"
DEFAULT_LANGUAGE = "en"
DEFAULT_META_IMAGE = "/static/img/default_img.png"
DEFAULT_TEMPLATE = "templates/base.html"
DEFAULT_THEME = "themes/basic.css"

# External services
EMOJI_SERVICE_URL = "https://emoji.dutl.uk/png/64x64/"

# Code highlighting options
CODEHILITE_OPTIONS = {
    "noclasses": True,
    "pygments_options": {"style": "colorful"},
    "css_class": "highlight",
    "use_pygments": True,
    "inline_css": True,
}


@dataclass
class RSSConfig:
    """Configuration for RSS feed generation."""

    whitelist: str = "*"
    description: str = "This is an RSS feed of my website."
    enabled: bool = True


@dataclass
class BuildConfig:
    """Configuration for build options."""

    include_drafts: bool = False
    incremental: bool = False


@dataclass
class ServerConfig:
    """Configuration for development server."""

    host: str = "127.0.0.1"
    port: int = 8000
    open_browser: bool = True


@dataclass
class Config:
    """Main configuration class for SimplyMarkdown."""

    input_dir: str = ""
    output_dir: str = ""
    template: str = DEFAULT_TEMPLATE
    theme: str = DEFAULT_THEME
    favicon: str = DEFAULT_FAVICON
    title: str = ""
    root_url: str = ""
    language: str = DEFAULT_LANGUAGE

    rss: RSSConfig = field(default_factory=RSSConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> Config:
        """Load configuration from a YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            return cls()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        rss_data = data.pop("rss", {})
        build_data = data.pop("build", {})
        server_data = data.pop("server", {})

        return cls(
            input_dir=data.get("input", data.get("input_dir", "")),
            output_dir=data.get("output", data.get("output_dir", "")),
            template=data.get("template", DEFAULT_TEMPLATE),
            theme=data.get("theme", data.get("css", DEFAULT_THEME)),
            favicon=data.get("favicon", DEFAULT_FAVICON),
            title=data.get("title", ""),
            root_url=data.get("root", data.get("root_url", "")),
            language=data.get("language", DEFAULT_LANGUAGE),
            rss=RSSConfig(**rss_data) if rss_data else RSSConfig(),
            build=BuildConfig(**build_data) if build_data else BuildConfig(),
            server=ServerConfig(**server_data) if server_data else ServerConfig(),
        )

    @classmethod
    def from_args(
        cls,
        input_dir: str,
        output_dir: str,
        template: str | None = None,
        css: str | None = None,
        favicon: str | None = None,
        title: str | None = None,
        root: str | None = None,
        rss_whitelist: str | None = None,
        rss_description: str | None = None,
        include_drafts: bool = False,
        incremental: bool = False,
    ) -> Config:
        """Create configuration from CLI arguments."""
        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            template=template or DEFAULT_TEMPLATE,
            theme=css or DEFAULT_THEME,
            favicon=favicon or DEFAULT_FAVICON,
            title=title or "",
            root_url=root or "",
            rss=RSSConfig(
                whitelist=rss_whitelist or "*",
                description=rss_description or "This is an RSS feed of my website.",
            ),
            build=BuildConfig(
                include_drafts=include_drafts,
                incremental=incremental,
            ),
        )

    def to_yaml(self, config_path: str | Path) -> None:
        """Save configuration to a YAML file."""
        data = {
            "input": self.input_dir,
            "output": self.output_dir,
            "template": self.template,
            "theme": self.theme,
            "favicon": self.favicon,
            "title": self.title,
            "root": self.root_url,
            "language": self.language,
            "rss": {
                "whitelist": self.rss.whitelist,
                "description": self.rss.description,
                "enabled": self.rss.enabled,
            },
            "build": {
                "include_drafts": self.build.include_drafts,
                "incremental": self.build.incremental,
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "open_browser": self.server.open_browser,
            },
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
