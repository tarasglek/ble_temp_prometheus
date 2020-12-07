#!/usr/bin/env python3
import http.server
import re
import sys
import time

class Prometheus(http.server.SimpleHTTPRequestHandler):
    stats = {}
    def do_GET(self):
        # Create an in-memory output file for the new workbook.
        self.send_response(200)
        self.end_headers()
        reply = ""
        timestamp = time.time()
        for sensor_name, items in Prometheus.stats.items():
            if timestamp > items['expiration']:
                continue
            for key, value in items.items():
                if key != "expiration":
                    reply = reply + f"""ble_sensor_value{{id="{sensor_name}", field="{key}"}} {value}\n"""
        self.wfile.write(reply.encode("utf-8"))
        return

    @staticmethod
    def run():
        import socketserver
        import threading
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(('', 9100), Prometheus)
        threading.Thread(target=lambda:httpd.serve_forever()).start()

p = re.compile(".*Service Data \(UUID 0x181a\): (............)..(..)(..)(..)(..)")

thermometers = {
    'a4c13885878e': 'garage',
    'a4c13884348e': 'garage bathroom',
    'a4c138863d06': 'basement',
    'a4c138946fa0': 'upstairs'
}
Prometheus.run()
for line in sys.stdin:
    line = line.rstrip()
    m = p.match(line)
    if not m:
        continue
    mac= m.groups()[0]
    (temp, humidity, battery, voltage) = map(lambda x:int(x, 16), m.groups()[1:])
    temp = temp/10.0
    name = thermometers.get(mac, mac)
    payload = {'temperature':temp, 'humidity':humidity, 'battery': battery, 'voltage':voltage}
    payload['expiration'] = time.time() + 120
    Prometheus.stats[name]=(payload)
    print(name)
    