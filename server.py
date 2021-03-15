#!/usr/bin/env python3
import sys
from datetime import datetime
import bluetooth._bluetooth as bluez
import http.server
import re
import time
from bluetooth_utils import (toggle_device, enable_le_scan,
                             parse_le_advertising_events,
                             disable_le_scan, raw_packet_to_str)
 

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

Prometheus.run()

thermometers = {
    'a4c13885878e': 'garage',
    'a4c13884348e': 'garage bathroom',
    'a4c138863d06': 'basement',
    'a4c138946fa0': 'upstairs',
    'a4c138dbbcaa': 'shed',
    'a4c138acbbef': 'compost-right',
    'a4c138493418': 'compost-left',
}
# Use 0 for hci0
dev_id = 0
toggle_device(dev_id, True)
 
try:
    sock = bluez.hci_open_dev(dev_id)
except:
    print("Cannot open bluetooth device %i" % dev_id)
    raise
 
# Set filter to "True" to see only one packet per device
enable_le_scan(sock, filter_duplicates=False)
p = re.compile("(............)..(..)(..)(..)(..)")

try:
    def le_advertise_packet_handler(mac, adv_type, data, rssi):
        data_str = raw_packet_to_str(data)
        # Check for ATC preamble
        if data_str[6:10] == '1a18':
            m = p.match(data_str[10:])
            mac= m.groups()[0]
            (temp, humidity, battery, voltage) = map(lambda x:int(x, 16), m.groups()[1:])
            temp = temp/10.0
            name = thermometers.get(mac, mac)
            payload = {'temperature':temp, 'humidity':humidity, 'battery': battery, 'voltage':voltage}
            payload['expiration'] = time.time() + 120
            Prometheus.stats[name]=(payload)
            print("%s - %s Temp: %sc Humidity: %s%% Batt: %s%%" % \
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, temp, humidity, battery))
 
    # Called on new LE packet
    parse_le_advertising_events(sock,
                                handler=le_advertise_packet_handler,
                                debug=False)
# Scan until Ctrl-C
except KeyboardInterrupt:
    disable_le_scan(sock)
