###############################################################################################
#  ______     __                                  __    __                   ______   ______  #
# /      \   /  |                                /  |  /  |                 /      \ /      | #
#/$$$$$$  | _$$ |_     ______   __    __         $$ |  $$ |  ______        /$$$$$$  |$$$$$$/  # 
#$$ \__$$/ / $$   |   /      \ /  |  /  | ______ $$ |  $$ | /      \       $$ |__$$ |  $$ |   # 
#$$      \ $$$$$$/    $$$$$$  |$$ |  $$ |/      |$$ |  $$ |/$$$$$$  |      $$    $$ |  $$ |   # 
# $$$$$$  |  $$ | __  /    $$ |$$ |  $$ |$$$$$$/ $$ |  $$ |$$ |  $$ |      $$$$$$$$ |  $$ |   # 
#/  \__$$ |  $$ |/  |/$$$$$$$ |$$ \__$$ |        $$ \__$$ |$$ |__$$ |      $$ |  $$ | _$$ |_  # 
#$$    $$/   $$  $$/ $$    $$ |$$    $$ |        $$    $$/ $$    $$/       $$ |  $$ |/ $$   | #
# $$$$$$/     $$$$/   $$$$$$$/  $$$$$$$ |         $$$$$$/  $$$$$$$/        $$/   $$/ $$$$$$/  # 
#                              /  \__$$ |                  $$ |                               # 
#                              $$    $$/                   $$ |                               #
#                               $$$$$$/                    $$/                                #
#                                                                                             #  
###############################################################################################
from __future__ import annotations

import atexit
import html
import os
import threading
import webbrowser
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import exifread
import folium

_MAP_SERVER = None
_MAP_SERVER_THREAD = None
_MAP_SERVER_ROOT = None
_MAP_SERVER_FILE = None
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP_OUTPUT_DIR = PROJECT_ROOT / "detected_files"

# Callers can surface this notice before opening a generated map.
USES_EXTERNAL_TILES = True
MAP_STORES_EXACT_COORDINATES = True
MAP_PRIVACY_NOTICE = (
    "지도 HTML에는 정확한 GPS 좌표가 저장되며, 지도를 표시할 때 "
    "OpenStreetMap 타일 서버로 네트워크 요청을 보냅니다."
)


@dataclass(frozen=True)
class GPSProcessingResult:
    """Describe GPS coverage without conflating absent and unreadable metadata."""

    location_count: int
    checked_count: int
    no_gps_count: int
    errors: tuple[str, ...]
    map_path: Path | None


class _LocalMapRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler for local map preview."""

    def __init__(self, *args, allowed_filename, **kwargs):
        self.allowed_filename = allowed_filename
        super().__init__(*args, **kwargs)

    def _is_allowed_request(self):
        request_path = unquote(urlsplit(self.path).path)
        return request_path == f"/{self.allowed_filename}"

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if not self._is_allowed_request():
            self.send_error(404)
            return

        super().do_GET()

    def do_HEAD(self):
        if not self._is_allowed_request():
            self.send_error(404)
            return

        super().do_HEAD()

    def log_message(self, format, *args):
        """Silence local preview HTTP logs."""
        return


def _ensure_local_http_server(map_file):
    """Serve only the generated map file over loopback HTTP."""
    global _MAP_SERVER, _MAP_SERVER_THREAD, _MAP_SERVER_ROOT, _MAP_SERVER_FILE

    map_path = Path(map_file).resolve()
    if not map_path.is_file():
        raise FileNotFoundError(f"지도 파일을 찾을 수 없습니다: {map_path}")

    directory = str(map_path.parent)
    map_file = str(map_path)
    if _MAP_SERVER is not None and _MAP_SERVER_FILE == map_file:
        return _MAP_SERVER.server_port

    if _MAP_SERVER is not None:
        _MAP_SERVER.shutdown()
        _MAP_SERVER.server_close()
        _MAP_SERVER = None
        _MAP_SERVER_THREAD = None
        _MAP_SERVER_ROOT = None
        _MAP_SERVER_FILE = None

    handler = partial(
        _LocalMapRequestHandler,
        directory=directory,
        allowed_filename=map_path.name,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    _MAP_SERVER = server
    _MAP_SERVER_THREAD = thread
    _MAP_SERVER_ROOT = directory
    _MAP_SERVER_FILE = map_file
    return server.server_port


def _shutdown_local_http_server():
    """Cleanly stop the local HTTP server on program exit."""
    global _MAP_SERVER, _MAP_SERVER_THREAD, _MAP_SERVER_ROOT, _MAP_SERVER_FILE
    if _MAP_SERVER is not None:
        _MAP_SERVER.shutdown()
        _MAP_SERVER.server_close()
        _MAP_SERVER = None
        _MAP_SERVER_THREAD = None
        _MAP_SERVER_ROOT = None
        _MAP_SERVER_FILE = None


atexit.register(_shutdown_local_http_server)


def _open_map_in_browser(output_html):
    """Open the generated HTML through a local HTTP server instead of file://."""
    output_path = Path(output_html).resolve()
    port = _ensure_local_http_server(output_path)
    url = f"http://127.0.0.1:{port}/{quote(output_path.name)}"
    return webbrowser.open(url)


def open_map_in_browser(output_html):
    """Open an already-created map and report whether a browser accepted it."""
    return _open_map_in_browser(output_html)


def _resolve_map_output_path(output_html):
    """Resolve relative map paths inside the ignored detection output directory."""
    output_path = Path(output_html).expanduser()
    if not output_path.is_absolute():
        output_path = DEFAULT_MAP_OUTPUT_DIR / output_path
    return output_path.resolve()


def _get_unique_output_path(output_html):
    """Return a path that does not overwrite an existing map file."""
    output_path = _resolve_map_output_path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not output_path.exists():
        return output_path

    counter = 1
    while True:
        candidate = output_path.with_name(
            f"{output_path.stem}_{counter}{output_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def extract_gps_data(image_path):
    """
    Extract GPS data from an image file.
    """
    with open(image_path, 'rb') as image_file:
        tags = exifread.process_file(image_file)

    # GPS data tags
    gps_latitude = tags.get('GPS GPSLatitude')
    gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
    gps_longitude = tags.get('GPS GPSLongitude')
    gps_longitude_ref = tags.get('GPS GPSLongitudeRef')

    # Check if GPS data exists
    if not all([gps_latitude, gps_latitude_ref, gps_longitude, gps_longitude_ref]):
        return None

    # Convert GPS coordinates to degrees
    def convert_to_degrees(value):
        d, m, s = [float(x.num) / float(x.den) for x in value.values]
        return d + (m / 60.0) + (s / 3600.0)

    latitude = convert_to_degrees(gps_latitude)
    if gps_latitude_ref.values[0] != 'N':
        latitude = -latitude

    longitude = convert_to_degrees(gps_longitude)
    if gps_longitude_ref.values[0] != 'E':
        longitude = -longitude

    return latitude, longitude

def plot_location_on_map(
    locations,
    output_html='map.html',
    open_browser=True,
    *,
    photo_names=None,
    should_cancel=None,
):
    """
    Plot GPS locations on a map and save as an HTML file.

    The HTML stores exact coordinates and loads external OpenStreetMap tiles.
    Callers should show MAP_PRIVACY_NOTICE before invoking this function.
    """
    if not locations:
        print("No locations to plot.")
        return

    output_path = _get_unique_output_path(output_html)

    # Initialize map centered at the first location
    center_lat, center_lon = locations[0]
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="OpenStreetMap")

    # Add markers for each location
    for index, (lat, lon) in enumerate(locations):
        popup = f"위도: {lat}<br>경도: {lon}"
        if photo_names is not None and index < len(photo_names):
            # Folium embeds popup HTML inside a JavaScript template literal.
            # Escape that context as well as HTML while retaining readable names.
            filename = html.escape(Path(photo_names[index]).name, quote=True)
            for character, entity in (("`", "&#96;"), ("$", "&#36;"), ("\\", "&#92;")):
                filename = filename.replace(character, entity)
            popup = f"사진: {filename}<br>{popup}"
        folium.Marker([lat, lon], popup=popup).add_to(m)

    if len({tuple(location) for location in locations}) > 1:
        m.fit_bounds(locations, padding=(24, 24), max_zoom=15)

    # Save the map to an HTML file
    if should_cancel is not None and should_cancel():
        raise InterruptedError("GPS 분석이 취소되었습니다.")
    m.save(str(output_path))
    print(f"Map saved as {output_path}")

    # Open the generated map in the default web browser via localhost
    if open_browser:
        _open_map_in_browser(output_path)

    return output_path


def list_original_images_in_folder(folder_path):
    """Return only top-level copied originals from the target folder."""
    folder = Path(folder_path).expanduser()
    image_paths = []

    if not folder.is_dir():
        print("GPS 분석 폴더를 찾을 수 없습니다.")
        return image_paths

    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if not path.name.startswith("original_"):
            continue
        if path.name.startswith("original_original_"):
            continue
        if path.suffix.lower() not in _IMAGE_EXTENSIONS:
            continue
        image_paths.append(str(path))

    return image_paths


def process_image_paths(
    image_paths,
    output_html="map.html",
    open_browser=True,
    output_directory=None,
):
    """Preserve the legacy integer return value for existing callers."""
    return process_image_paths_detailed(
        image_paths,
        output_html=output_html,
        open_browser=open_browser,
        output_directory=output_directory,
    ).location_count


def process_image_paths_detailed(
    image_paths,
    output_html="map.html",
    open_browser=True,
    output_directory=None,
    *,
    should_cancel=None,
):
    """Extract GPS data from current images, isolating per-file EXIF failures.

    Relative output names are stored in DEFAULT_MAP_OUTPUT_DIR. Pass
    output_directory to select an explicit detection or user-data directory.
    The result separates missing GPS from per-file errors and includes the saved
    map path. Map creation errors propagate to the caller. An optional cancellation
    callback raises InterruptedError between files and before the map is saved.
    """
    if isinstance(image_paths, (str, os.PathLike)):
        image_paths = [image_paths]

    locations = []
    photo_names = []
    seen_paths = set()
    checked_count = 0
    no_gps_count = 0
    errors = []

    def check_cancelled():
        if should_cancel is not None and should_cancel():
            raise InterruptedError("GPS 분석이 취소되었습니다.")

    for image_path in image_paths or []:
        check_cancelled()
        try:
            path = Path(image_path).expanduser()
            normalized_path = str(path.resolve())
        except (TypeError, ValueError, OSError, RuntimeError):
            checked_count += 1
            errors.append("올바르지 않은 GPS 분석 경로를 건너뜁니다.")
            continue

        if normalized_path in seen_paths:
            continue

        seen_paths.add(normalized_path)
        checked_count += 1

        try:
            if not path.is_file():
                errors.append(f"{path.name}: 사진 파일을 찾을 수 없습니다.")
                continue
            if path.suffix.lower() not in _IMAGE_EXTENSIONS:
                errors.append(f"{path.name}: 지원하지 않는 사진 형식입니다.")
                continue
            gps_data = extract_gps_data(path)
        except Exception as error:
            message = f"GPS 정보를 읽지 못했습니다 ({path.name}): {error}"
            errors.append(message)
            print(message)
            continue

        if gps_data:
            locations.append(gps_data)
            photo_names.append(path.name)
        else:
            no_gps_count += 1

    check_cancelled()
    map_path = None
    if locations:
        if output_directory is not None:
            output_html = Path(output_directory).expanduser() / Path(output_html).name
        map_path = plot_location_on_map(
            locations,
            output_html=output_html,
            open_browser=open_browser,
            photo_names=photo_names,
            should_cancel=should_cancel,
        )
        print(f"탐지된 위치가 지도에 {len(locations)}곳이 표시되었습니다.")
    else:
        print("탐지된 위치가 없습니다.")
    return GPSProcessingResult(
        location_count=len(locations),
        checked_count=checked_count,
        no_gps_count=no_gps_count,
        errors=tuple(errors),
        map_path=map_path,
    )

def process_images_in_folder(
    folder_path,
    image_paths=None,
    output_directory=None,
    open_browser=True,
):
    """
    Process explicit paths, or preserve the legacy original_* folder scan.

    Pass image_paths to map only files from the current detection run.
    """
    if image_paths is None:
        image_paths = list_original_images_in_folder(folder_path)
    return process_image_paths(
        image_paths,
        output_directory=output_directory,
        open_browser=open_browser,
    )
