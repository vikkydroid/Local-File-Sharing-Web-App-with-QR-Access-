import os
import socket
import socketserver
import http.server
import pyqrcode
import webbrowser
import html
import posixpath
from urllib.parse import unquote, urlparse, parse_qs
from jinja2 import Environment, FileSystemLoader
import logging

PORT = 8010

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Project directory (where templates and static folder are)
project_dir = r"C:\Users\lenovo\Documents\Python\Python_Projects\1_FileSharing_App"

# Change working directory to project_dir so static files are served correctly
os.chdir(project_dir)

env = Environment(loader=FileSystemLoader('templates'))

# Add custom Jinja2 filter to URL decode strings for display in templates
def url_unquote_filter(s):
    return unquote(s)

env.filters['url_unquote'] = url_unquote_filter

# Directory to serve files from (your file root)
FILE_ROOT_DIR = r"C:\Users\lenovo\Documents"

try:
    hostname = socket.gethostname()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    base_url = f"http://{ip_address}:{PORT}"
    logging.info(f"Server base URL: {base_url}")
except socket.error as e:
    logging.error(f"Failed to get local IP address: {e}")
    exit(1)

# Generate QR code only if it does not exist
if not os.path.exists("myqr.svg"):
    qr = pyqrcode.create(base_url)
    qr.svg("myqr.svg", scale=8)
    logging.info("Generated QR code SVG.")

try:
    with open("myqr.svg", "r", encoding="utf-8") as f:
        qr_svg = f.read()
except FileNotFoundError:
    logging.error("QR code SVG file not found.")
    exit(1)

try:
    template = env.get_template("qr_landing.html")
    qr_html = template.render(qr_svg=qr_svg, target_link=base_url)
    with open(os.path.join("templates", "qr_landing.html"), "w", encoding="utf-8") as f:
        f.write(qr_html)
    logging.info("Generated 'qr_landing.html' from template.")
except Exception as e:
    logging.error(f"Failed to generate QR landing page: {e}")
    exit(1)


class PrettyHandler(http.server.SimpleHTTPRequestHandler):
    file_root = FILE_ROOT_DIR

    def translate_path(self, path):
        """
        Override to serve files relative to FILE_ROOT_DIR instead of cwd.
        Decodes URL, normalizes path to prevent directory traversal,
        then joins with file_root.
        """
        # Remove query parameters and fragments
        path = urlparse(path).path
        # Decode URL-encoded path (%20, etc)
        path = unquote(path)
        # Remove leading slash for relative path join
        path = path.lstrip("/")
        # Normalize to prevent directory traversal attacks (../)
        path = os.path.normpath(path)
        if path.startswith(".."):
            path = ""
        # Construct full filesystem path
        full_path = os.path.join(self.file_root, path)
        return full_path

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Serve static assets from /static/ folder inside project_dir
        if path.startswith("/static/"):
            # Serve file relative to project_dir/static
            static_file_path = os.path.join(project_dir, path.lstrip("/"))
            if os.path.isfile(static_file_path):
                try:
                    with open(static_file_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    # Simple content type detection for css, js, svg
                    if path.endswith(".css"):
                        self.send_header("Content-type", "text/css; charset=utf-8")
                    elif path.endswith(".js"):
                        self.send_header("Content-type", "application/javascript")
                    elif path.endswith(".svg"):
                        self.send_header("Content-type", "image/svg+xml")
                    else:
                        self.send_header("Content-type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    logging.error(f"Error serving static file {static_file_path}: {e}")
                    self.send_error(500, "Internal server error serving static file")
            else:
                self.send_error(404, "Static file not found")
            return

        # Serve QR landing page ONLY on /qr
        if path == "/qr":
            try:
                with open(os.path.join("templates", "qr_landing.html"), "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "QR landing page not found")
            return

        # Serve directory listing or file from FILE_ROOT_DIR
        full_path = self.translate_path(path)

        if os.path.isdir(full_path):
            # Accept "view" query param: "tile" or "detail"
            view_mode = query_params.get("view", ["tile"])[0].lower()
            if view_mode not in ("tile", "detail"):
                view_mode = "tile"
            self.list_directory(full_path, view_mode)
            return

        if os.path.isfile(full_path):
            # Serve file from FILE_ROOT_DIR by temporarily changing cwd for base handler
            cwd = os.getcwd()
            try:
                os.chdir(self.file_root)
                # Rewrite path relative to file_root (remove leading slash)
                self.path = "/" + os.path.relpath(full_path, self.file_root).replace("\\", "/")
                return http.server.SimpleHTTPRequestHandler.do_GET(self)
            finally:
                os.chdir(cwd)
        else:
            self.send_error(404, "File not found")
            return

    def list_directory(self, path, view_mode="tile"):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "Cannot list directory")
            return None

        entries.sort()
        display_path = html.escape(self.path)
        parent_link = None
        if self.path != "/":
            parent_link = posixpath.dirname(self.path.rstrip("/"))
            if not parent_link.startswith("/"):
                parent_link = "/" + parent_link
            if parent_link == "":
                parent_link = "/"

        items = []
        current_path = self.path.rstrip('/')
        for name in entries:
            fullname = os.path.join(path, name)
            displayname = name
            href = posixpath.join(current_path, name)  # <-- DO NOT QUOTE HERE TO AVOID DOUBLE ENCODING
            if os.path.isdir(fullname):
                displayname += "/"
                href += "/"  # trailing slash for folders
                item_type = "folder"
                size = "-"
            else:
                item_type = "file"
                try:
                    size = f"{os.path.getsize(fullname) / 1024:.1f} KB"
                except OSError:
                    size = "N/A"
            items.append({
                'name': displayname,
                'href': href,
                'type': item_type,
                'size': size
            })

        template = env.get_template("directory.html")
        html_response = template.render(
            path=display_path,
            entries=items,
            parent_link=parent_link,
            view_mode=view_mode
        )

        encoded = html_response.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_request(self, code='-', size='-'):
        logging.info(
            f'{self.client_address[0]} - - [{self.log_date_time_string()}] '
            f'"{self.command} {self.path} {self.request_version}" {code} {size}'
        )


if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), PrettyHandler) as httpd:
            logging.info(f"Serving at {base_url}")
            logging.info(f"Open the QR landing page at {base_url}/qr")
            webbrowser.open(f"{base_url}/qr")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
