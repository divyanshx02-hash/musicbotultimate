#!/usr/bin/env python3
"""Simple HTTP server to serve the MusicBot.zip download."""
import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

os.chdir(DIRECTORY)

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/download':
            self.path = '/MusicBot.zip'
        return super().do_GET()

    def end_headers(self):
        if self.path.endswith('.zip'):
            self.send_header('Content-Disposition', 'attachment; filename=MusicBot.zip')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Download server running at http://localhost:{PORT}")
    print(f"Download link: http://localhost:{PORT}/MusicBot.zip")
    httpd.serve_forever()
