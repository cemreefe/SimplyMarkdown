"""Development server for SimplyMarkdown."""

from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
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


LIVE_RELOAD_SCRIPT = """
<script>
(function() {
  const es = new EventSource('/__livereload');
  es.onmessage = function() { location.reload(); };
  es.onerror = function() { es.close(); };
})();
</script>
"""


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that suppresses logging."""

    def log_message(self, format: str, *args) -> None:
        """Suppress log messages."""
        pass


class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with live reload support."""

    last_rebuild: float = 0.0
    live_reload_enabled: bool = False

    def log_message(self, format: str, *args) -> None:
        """Suppress log messages except errors."""
        if args and "500" in str(args[0]):
            super().log_message(format, *args)

    def do_GET(self) -> None:
        """Handle GET requests with live reload and .html extension handling."""
        # SSE endpoint for live reload
        if self.path == "/__livereload" and self.live_reload_enabled:
            self._handle_livereload_sse()
            return

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

        # If live reload is enabled and this is an HTML file, inject the script
        if self.live_reload_enabled and self._is_html_request():
            self._serve_html_with_livereload()
        else:
            super().do_GET()

    def _is_html_request(self) -> bool:
        """Check if the request is for an HTML file."""
        path = self.path.split("?")[0]
        if path.endswith(".html"):
            return True
        if path.endswith("/"):
            index_path = os.path.join(self.directory, path.lstrip("/"), "index.html")
            return os.path.exists(index_path)
        return False

    def _handle_livereload_sse(self) -> None:
        """Handle Server-Sent Events for live reload."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_seen = self.last_rebuild

        try:
            while True:
                if self.last_rebuild > last_seen:
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                    last_seen = self.last_rebuild
                time.sleep(0.3)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_html_with_livereload(self) -> None:
        """Serve HTML file with live reload script injected."""
        path = self.translate_path(self.path)

        try:
            with open(path, "rb") as f:
                content = f.read()
        except (FileNotFoundError, IsADirectoryError):
            # Try index.html for directory requests
            if self.path.endswith("/"):
                path = os.path.join(path, "index.html")
                try:
                    with open(path, "rb") as f:
                        content = f.read()
                except FileNotFoundError:
                    self.send_error(404, "File not found")
                    return
            else:
                self.send_error(404, "File not found")
                return

        # Inject live reload script before </body>
        content_str = content.decode("utf-8", errors="replace")
        if "</body>" in content_str:
            content_str = content_str.replace("</body>", LIVE_RELOAD_SCRIPT + "</body>")
        else:
            content_str += LIVE_RELOAD_SCRIPT

        content = content_str.encode("utf-8")

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass


class RebuildHandler(FileSystemEventHandler):
    """Handler for file system events to trigger rebuilds."""

    def __init__(
        self,
        callback: Callable[[], None],
        debounce_seconds: float = 0.5,
        handler_class: type | None = None,
    ):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.handler_class = handler_class
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
            # Signal browsers to reload
            if self.handler_class:
                self.handler_class.last_rebuild = time.time()
            print("✅ Build complete!")
        except Exception as e:
            print(f"❌ Build failed: {e}")


def serve(
    output_dir: str | Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
    live_reload: bool = False,
) -> None:
    """Start a development server.

    Args:
        output_dir: Directory to serve files from.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser automatically.
        live_reload: Whether to enable live reload.
    """
    output_dir = Path(output_dir).resolve()

    LiveReloadHandler.live_reload_enabled = live_reload

    handler = partial(LiveReloadHandler, directory=str(output_dir))

    # Use threading server to handle multiple concurrent requests
    # (needed for SSE live reload endpoint)
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ThreadingHTTPServer((host, port), handler) as httpd:
        url = f"http://{host}:{port}"
        print(f"🌐 Serving at {url}")
        if live_reload:
            print("   🔄 Live reload enabled")
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
    handler_class: type | None = None,
) -> Observer | None:
    """Watch a directory for changes and trigger rebuilds.

    Args:
        input_dir: Directory to watch for changes.
        rebuild_callback: Function to call when changes are detected.
        handler_class: Optional handler class to signal for live reload.

    Returns:
        Observer instance if watchdog is available, None otherwise.
    """
    if not WATCHDOG_AVAILABLE:
        print("⚠️  Watch mode requires 'watchdog' package.")
        print("   Install with: pip install watchdog")
        return None

    input_dir = Path(input_dir).resolve()
    event_handler = RebuildHandler(rebuild_callback, handler_class=handler_class)
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
    """Start development server with file watching and live reload.

    Args:
        input_dir: Directory to watch for changes.
        output_dir: Directory to serve files from.
        rebuild_callback: Function to call when changes are detected.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser automatically.
    """
    # Start watcher with live reload support
    observer = watch(input_dir, rebuild_callback, handler_class=LiveReloadHandler)

    try:
        # Start server with live reload enabled (blocks until interrupted)
        serve(output_dir, host, port, open_browser, live_reload=True)
    finally:
        if observer:
            observer.stop()
            observer.join()
