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
import atexit
import os
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

import exifread
import folium


_MAP_SERVER = None
_MAP_SERVER_THREAD = None
_MAP_SERVER_ROOT = None


class _LocalMapRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler for local map preview."""

    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, format, *args):
        """Silence local preview HTTP logs."""
        return


def _ensure_local_http_server(directory):
    """Serve generated map files over HTTP so tile requests include a Referer."""
    global _MAP_SERVER, _MAP_SERVER_THREAD, _MAP_SERVER_ROOT

    directory = str(Path(directory).resolve())
    if _MAP_SERVER is not None and _MAP_SERVER_ROOT == directory:
        return _MAP_SERVER.server_port

    if _MAP_SERVER is not None:
        _MAP_SERVER.shutdown()
        _MAP_SERVER.server_close()
        _MAP_SERVER = None
        _MAP_SERVER_THREAD = None
        _MAP_SERVER_ROOT = None

    handler = partial(_LocalMapRequestHandler, directory=directory)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    _MAP_SERVER = server
    _MAP_SERVER_THREAD = thread
    _MAP_SERVER_ROOT = directory
    return server.server_port


def _shutdown_local_http_server():
    """Cleanly stop the local HTTP server on program exit."""
    global _MAP_SERVER, _MAP_SERVER_THREAD, _MAP_SERVER_ROOT
    if _MAP_SERVER is not None:
        _MAP_SERVER.shutdown()
        _MAP_SERVER.server_close()
        _MAP_SERVER = None
        _MAP_SERVER_THREAD = None
        _MAP_SERVER_ROOT = None


atexit.register(_shutdown_local_http_server)


def _open_map_in_browser(output_html):
    """Open the generated HTML through a local HTTP server instead of file://."""
    output_path = Path(output_html).resolve()
    port = _ensure_local_http_server(output_path.parent)
    url = f"http://127.0.0.1:{port}/{quote(output_path.name)}"
    webbrowser.open(url)

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

def plot_location_on_map(locations, output_html='map.html'):
    """
    Plot GPS locations on a map and save as an HTML file.
    """
    if not locations:
        print("No locations to plot.")
        return

    output_path = Path(output_html).resolve()

    # Initialize map centered at the first location
    center_lat, center_lon = locations[0]
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="OpenStreetMap")

    # Add markers for each location
    for lat, lon in locations:
        folium.Marker([lat, lon], popup=f"Location: {lat}, {lon}").add_to(m)

    # Save the map to an HTML file
    m.save(str(output_path))
    print(f"Map saved as {output_path}")

    # Open the generated map in the default web browser via localhost
    _open_map_in_browser(output_path)

def process_images_in_folder(folder_path):
    """
    Process all images in the specified folder and extract GPS data.
    """
    locations = []
    for file_name in os.listdir(folder_path):
        # 파일 이름이 'original_'로 시작하는지 확인
        if not file_name.startswith("original_"):
            continue

        # 파일 확장자가 이미지인지 확인
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(folder_path, file_name)
            gps_data = extract_gps_data(image_path)
            if gps_data:
                locations.append(gps_data)                
                # print(f"GPS Data for {file_name}: {gps_data}")
                

            else:
                # print(f"No GPS Data for {file_name}")
                # print("탐지된 위치가 없습니다.")
                pass

    # Plot the locations on a map
    if locations:
        plot_location_on_map(locations)
        print(f"탐지된 위치가 지도에 {len(locations)}곳이 표시되었습니다.")
    else:
        print("탐지된 위치가 없습니다.")
