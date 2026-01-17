"""Tests for configuration handling."""

import tempfile
from pathlib import Path

import pytest

from simplymarkdown.config import (
    Config,
    RSSConfig,
    BuildConfig,
    ServerConfig,
    DEFAULT_FAVICON,
    DEFAULT_TEMPLATE,
    DEFAULT_THEME,
)


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self) -> None:
        config = Config()
        
        assert config.input_dir == ""
        assert config.output_dir == ""
        assert config.template == DEFAULT_TEMPLATE
        assert config.theme == DEFAULT_THEME
        assert config.favicon == DEFAULT_FAVICON
        assert config.title == ""
        assert config.root_url == ""

    def test_custom_values(self) -> None:
        config = Config(
            input_dir="source",
            output_dir="build",
            title="My Blog",
            root_url="https://example.com",
        )
        
        assert config.input_dir == "source"
        assert config.output_dir == "build"
        assert config.title == "My Blog"
        assert config.root_url == "https://example.com"

    def test_rss_config(self) -> None:
        rss = RSSConfig(
            whitelist="/posts/*",
            description="My feed",
            enabled=True,
        )
        config = Config(rss=rss)
        
        assert config.rss.whitelist == "/posts/*"
        assert config.rss.description == "My feed"
        assert config.rss.enabled is True

    def test_build_config(self) -> None:
        build = BuildConfig(
            include_drafts=True,
            incremental=True,
        )
        config = Config(build=build)
        
        assert config.build.include_drafts is True
        assert config.build.incremental is True

    def test_server_config(self) -> None:
        server = ServerConfig(
            host="0.0.0.0",
            port=3000,
            open_browser=False,
        )
        config = Config(server=server)
        
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 3000
        assert config.server.open_browser is False


class TestConfigYaml:
    """Tests for YAML configuration loading/saving."""

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Create and save config
            original = Config(
                input_dir="source",
                output_dir="output",
                title="Test Blog",
                root_url="https://test.com",
                favicon="🚀",
            )
            original.to_yaml(config_path)
            
            # Load config
            loaded = Config.from_yaml(config_path)
            
            assert loaded.input_dir == original.input_dir
            assert loaded.output_dir == original.output_dir
            assert loaded.title == original.title
            assert loaded.root_url == original.root_url
            assert loaded.favicon == original.favicon

    def test_load_nonexistent_file(self) -> None:
        config = Config.from_yaml("/nonexistent/path/config.yaml")
        
        # Should return default config
        assert config.input_dir == ""
        assert config.output_dir == ""

    def test_from_args(self) -> None:
        config = Config.from_args(
            input_dir="src",
            output_dir="dist",
            title="CLI Blog",
            root="https://cli.com",
            include_drafts=True,
        )
        
        assert config.input_dir == "src"
        assert config.output_dir == "dist"
        assert config.title == "CLI Blog"
        assert config.root_url == "https://cli.com"
        assert config.build.include_drafts is True
