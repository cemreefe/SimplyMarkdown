"""Command-line interface for SimplyMarkdown."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from simplymarkdown import __version__
from simplymarkdown.config import (
    DEFAULT_FAVICON,
    DEFAULT_TEMPLATE,
    DEFAULT_THEME,
    BuildConfig,
    Config,
    RSSConfig,
)
from simplymarkdown.renderer import render_site
from simplymarkdown.server import serve, serve_with_watch


@click.group()
@click.version_option(version=__version__, prog_name="SimplyMarkdown")
def cli() -> None:
    """SimplyMarkdown - Convert your Markdown into a Website.

    A lightweight static site generator that transforms Markdown files
    into a fully-functional website.
    """
    pass


@cli.command()
@click.option("-i", "--input", "input_dir", required=True, help="Input directory path")
@click.option("-o", "--output", "output_dir", required=True, help="Output directory path")
@click.option("--css", "theme", default=DEFAULT_THEME, help="CSS theme file path")
@click.option("--template", default=DEFAULT_TEMPLATE, help="HTML template path")
@click.option("--favicon", default=DEFAULT_FAVICON, help="Favicon emoji")
@click.option("--root", "root_url", default="", help="Root URL for the site")
@click.option("--title", default="", help="Website title")
@click.option("--rss-whitelist", default="*", help="RSS feed URI whitelist patterns")
@click.option("--rss-description", default="This is an RSS feed.", help="RSS feed description")
@click.option("--include-drafts", is_flag=True, help="Include draft posts")
@click.option("--incremental", is_flag=True, help="Only rebuild changed files")
@click.option("--watch", "watch_mode", is_flag=True, help="Watch for changes and rebuild")
@click.option("--serve", "serve_mode", is_flag=True, help="Start development server")
@click.option("--port", default=8000, help="Development server port")
@click.option("--no-open", is_flag=True, help="Don't open browser automatically")
def build(
    input_dir: str,
    output_dir: str,
    theme: str,
    template: str,
    favicon: str,
    root_url: str,
    title: str,
    rss_whitelist: str,
    rss_description: str,
    include_drafts: bool,
    incremental: bool,
    watch_mode: bool,
    serve_mode: bool,
    port: int,
    no_open: bool,
) -> None:
    """Build the static site from Markdown files.

    Examples:

        simplymarkdown build -i source -o output

        simplymarkdown build -i source -o output --watch --serve

        simplymarkdown build -i source -o output --title "My Blog" --root https://myblog.com
    """
    # Resolve paths
    input_path = Path(input_dir).resolve()
    output_path = Path(output_dir).resolve()

    if not input_path.exists():
        click.echo(f"❌ Error: Input directory does not exist: {input_path}", err=True)
        sys.exit(1)

    # Create config
    config = Config(
        input_dir=str(input_path),
        output_dir=str(output_path),
        template=template,
        theme=theme,
        favicon=favicon,
        title=title,
        root_url=root_url,
        rss=RSSConfig(
            whitelist=rss_whitelist,
            description=rss_description,
        ),
        build=BuildConfig(
            include_drafts=include_drafts,
            incremental=incremental,
        ),
    )

    def do_build() -> None:
        """Perform the build."""
        render_site(config)

    # Initial build
    click.echo("🔨 Building site...")
    click.echo(f"   Input:  {input_path}")
    click.echo(f"   Output: {output_path}")

    try:
        do_build()
        click.echo("✅ Build complete!")
    except Exception as e:
        click.echo(f"❌ Build failed: {e}", err=True)
        if not (watch_mode or serve_mode):
            sys.exit(1)

    # Watch and/or serve mode
    if watch_mode or serve_mode:
        if serve_mode and watch_mode:
            serve_with_watch(
                input_path,
                output_path,
                do_build,
                port=port,
                open_browser=not no_open,
            )
        elif serve_mode:
            serve(output_path, port=port, open_browser=not no_open)
        elif watch_mode:
            from simplymarkdown.server import watch as watch_dir

            observer = watch_dir(input_path, do_build)
            if observer:
                try:
                    click.echo("Press Ctrl+C to stop watching...")
                    while True:
                        observer.join(1)
                except KeyboardInterrupt:
                    click.echo("\n👋 Stopped watching")
                    observer.stop()
                    observer.join()


@cli.command()
@click.argument("output_dir")
@click.option("--port", default=8000, help="Server port")
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--no-open", is_flag=True, help="Don't open browser automatically")
def server(output_dir: str, port: int, host: str, no_open: bool) -> None:
    """Start a development server.

    Example:

        simplymarkdown serve output/
    """
    output_path = Path(output_dir).resolve()

    if not output_path.exists():
        click.echo(f"❌ Error: Output directory does not exist: {output_path}", err=True)
        sys.exit(1)

    serve(output_path, host=host, port=port, open_browser=not no_open)


@cli.command()
@click.argument("project_dir", default=".")
@click.option("--title", prompt="Website title", help="Title of the website")
@click.option("--root", "root_url", prompt="Root URL (e.g., https://myblog.com)", help="Root URL")
@click.option("--favicon", default="🌐", help="Favicon emoji")
def init(project_dir: str, title: str, root_url: str, favicon: str) -> None:
    """Initialize a new SimplyMarkdown project.

    Example:

        simplymarkdown init my-blog
    """
    project_path = Path(project_dir).resolve()

    # Create directory structure
    dirs = [
        "source",
        "source/posts",
        "source/modules",
        "source/static/img",
        "source/static/css",
        "output",
    ]

    for dir_path in dirs:
        (project_path / dir_path).mkdir(parents=True, exist_ok=True)

    # Create config file
    config = Config(
        input_dir="source",
        output_dir="output",
        title=title,
        root_url=root_url,
        favicon=favicon,
    )
    config.to_yaml(project_path / "simplymarkdown.yaml")

    # Create index.md
    index_content = f"""---
title: {title}
---

# Welcome to {title}

This is your new SimplyMarkdown website!

% posts
"""
    (project_path / "source" / "index.md").write_text(index_content)

    # Create navbar module
    navbar_content = """[Home](/) | [About](/about)
"""
    (project_path / "source" / "modules" / "navbar.md").write_text(navbar_content)

    # Create footer module
    footer_content = """---

Made with [SimplyMarkdown](https://github.com/cemreefe/SimplyMarkdown)
"""
    (project_path / "source" / "modules" / "footer.md").write_text(footer_content)

    # Create about page
    about_content = """---
title: About
---

# About

This is the about page for your website.
"""
    (project_path / "source" / "about.md").write_text(about_content)

    # Create example post
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")

    post_content = f"""---
title: My First Post
date: {today}
emoji: 🎉
tags: welcome
---

# My First Post

Welcome to my new blog! This is my first post.
"""
    posts_dir = project_path / "source" / "posts" / datetime.now().strftime("%Y/%m/%d")
    posts_dir.mkdir(parents=True, exist_ok=True)
    (posts_dir / "my-first-post.md").write_text(post_content)

    click.echo(f"✅ Project initialized at {project_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. cd {project_dir}")
    click.echo("  2. simplymarkdown build -i source -o output --serve")
    click.echo()
    click.echo("Or use the config file:")
    click.echo("  simplymarkdown build --config simplymarkdown.yaml --serve")


@cli.command()
@click.argument("title")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def new(title: str, project_dir: str) -> None:
    """Create a new blog post.

    Example:

        simplymarkdown new "My New Post"
    """
    from datetime import datetime

    project_path = Path(project_dir).resolve()
    source_dir = project_path / "source"

    if not source_dir.exists():
        source_dir = project_path

    # Create post
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    posts_dir = source_dir / "posts" / today.strftime("%Y/%m/%d")
    posts_dir.mkdir(parents=True, exist_ok=True)

    # Slugify title
    slug = title.lower().replace(" ", "-").replace(",", "")

    post_content = f"""---
title: {title}
date: {date_str}
emoji: ✨
tags:
draft: true
---

# {title}

Write your content here...
"""

    post_path = posts_dir / f"{slug}.md"

    if post_path.exists():
        click.echo(f"❌ Error: Post already exists: {post_path}", err=True)
        sys.exit(1)

    post_path.write_text(post_content)
    click.echo(f"✅ Created new post: {post_path}")
    click.echo()
    click.echo("Note: Post is created as a draft. Remove 'draft: true' to publish.")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
