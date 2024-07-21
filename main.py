import mimetypes
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket
from pymongo import MongoClient
from datetime import datetime
from multiprocessing import Process
import ast


client = MongoClient('localhost', 27017)
db = client['messages_db']
collection = db['messages']

class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data_parse = urllib.parse.unquote_plus(post_data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 5000))
            sock.sendall(str(data_dict).encode('utf-8'))

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        elif pr_url.path.startswith('/static/'):
            self.send_static_file(pr_url.path[1:])
        else:
            self.send_html_file('error.html', status=404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static_file(self, path):
        file_path = pathlib.Path('static') / path
        if file_path.exists():
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                self.send_header('Content-type', mime_type)
            else:
                self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_html_file('error.html', status=404)

def run_http_server():
    server_address = ('', 3000)
    httpd = HTTPServer(server_address, HttpHandler)
    print("HTTP server running on port 3000")
    httpd.serve_forever()

def run_socket_server():
    server_address = ('localhost', 5000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(1)
    print('Socket server listening on port 5000...')

    while True:
        connection, client_address = sock.accept()
        try:
            data = connection.recv(1024)
            if data:
                data_dict = ast.literal_eval(data.decode('utf-8'))
                data_dict['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

                collection.insert_one(data_dict)
                print(f"Saved to MongoDB: {data_dict}")
        finally:
            connection.close()

if __name__ == '__main__':
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()
