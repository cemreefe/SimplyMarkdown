"""
SimplyMarkdown - Convert your Markdown into a Website

A lightweight static site generator that transforms Markdown files into
a fully-functional website with minimal configuration.
"""

__version__ = "2.0.0"
__author__ = "cemreefe"

from simplymarkdown.config import Config
from simplymarkdown.renderer import render_site

__all__ = ["render_site", "Config", "__version__"]
