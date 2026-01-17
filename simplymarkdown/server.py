"""Development server for SimplyMarkdown."""

from __future__ import annotations

import http.server
import os
import socketserver
import threading
import webbrowser
from collections.abc import Callable
from functools import partial
from pathlib import Path

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses logging."""

    def log_message(self, format: str, *args) -> None:
        """Suppress log messages."""
        pass


class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with live reload support."""

    def log_message(self, format: str, *args) -> None:
        """Suppress log messages except errors."""
        if args and "404" in str(args[0]):
            pass  # Suppress 404s
        elif args and "500" in str(args[0]):
            super().log_message(format, *args)

    def do_GET(self) -> None:
        """Handle GET requests with .html extension handling."""
        # Try adding .html extension for clean URLs
        if not self.path.endswith(
            (
                "/",
                ".html",
                ".css",
                ".js",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".ico",
                ".xml",
                ".json",
            )
        ):
            html_path = self.path + ".html"
            full_path = os.path.join(self.directory, html_path.lstrip("/"))
            if os.path.exists(full_path):
                self.path = html_path

        super().do_GET()


class RebuildHandler(FileSystemEventHandler):
    """Handler for file system events to trigger rebuilds."""

    def __init__(self, callback: Callable[[], None], debounce_seconds: float = 0.5):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        if event.is_directory:
            return

        # Ignore hidden files and common temp files
        src_path = getattr(event, "src_path", "")
        if any(part.startswith(".") for part in Path(src_path).parts):
            return
        if src_path.endswith((".swp", ".tmp", "~")):
            return

        # Debounce rapid events
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._trigger)
            self._timer.start()

    def _trigger(self) -> None:
        """Trigger the rebuild callback."""
        print("\n🔄 Changes detected, rebuilding...")
        try:
            self.callback()
            print("✅ Build complete!")
        except Exception as e:
            print(f"❌ Build failed: {e}")


def serve(
    output_dir: str | Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
) -> None:
    """Start a development server.

    Args:
        output_dir: Directory to serve files from.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser automatically.
    """
    output_dir = Path(output_dir).resolve()

    handler = partial(LiveReloadHandler, directory=str(output_dir))

    with socketserver.TCPServer((host, port), handler) as httpd:
        url = f"http://{host}:{port}"
        print(f"🌐 Serving at {url}")
        print("   Press Ctrl+C to stop")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


def watch(
    input_dir: str | Path,
    rebuild_callback: Callable[[], None],
) -> Observer | None:
    """Watch a directory for changes and trigger rebuilds.

    Args:
        input_dir: Directory to watch for changes.
        rebuild_callback: Function to call when changes are detected.

    Returns:
        Observer instance if watchdog is available, None otherwise.
    """
    if not WATCHDOG_AVAILABLE:
        print("⚠️  Watch mode requires 'watchdog' package.")
        print("   Install with: pip install watchdog")
        return None

    input_dir = Path(input_dir).resolve()
    event_handler = RebuildHandler(rebuild_callback)
    observer = Observer()
    observer.schedule(event_handler, str(input_dir), recursive=True)
    observer.start()

    print(f"👀 Watching {input_dir} for changes...")
    return observer


def serve_with_watch(
    input_dir: str | Path,
    output_dir: str | Path,
    rebuild_callback: Callable[[], None],
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
) -> None:
    """Start development server with file watching.

    Args:
        input_dir: Directory to watch for changes.
        output_dir: Directory to serve files from.
        rebuild_callback: Function to call when changes are detected.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser automatically.
    """
    # Start watcher
    observer = watch(input_dir, rebuild_callback)

    try:
        # Start server (blocks until interrupted)
        serve(output_dir, host, port, open_browser)
    finally:
        if observer:
            observer.stop()
            observer.join()
