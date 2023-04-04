"""
	Trigger external led by http request
	
	:author:	Roberto Bellingeri
	:copyright:	Copyright 2022 - NetGuru
	:license:	GPL
"""

"""
	Changelog:
	
	0.0.1	
			initial release
"""

from machine import Pin
import time
import network
import uasyncio as asyncio

import config as cfg

network.hostname(cfg.WIFI_HOSTNAME) # type: ignore
wlan = network.WLAN(network.STA_IF)
led_onboard = Pin("LED", Pin.OUT)
led_external = Pin(cfg.LED_PIN, Pin.OUT)

template = ""

def connect_to_network():
	"""
	Try to connect internet
	"""
	wlan.active(True)
	wlan.config(pm = 0xa11140) # type: ignore - Disable power-save mode
	wlan.connect(cfg.WIFI_SSID, cfg.WIFI_PASSWORD)

	# Wait for connect or fail
	n = 0
	while (n < cfg.WIFI_MAXWAIT):
		if ((wlan.status() < 0) or (wlan.status() >= 3)):
			break
		n += 1
		print("Waiting for connection...")
		time.sleep(1)
	
	# Handle connection error
	if (wlan.status() != 3):
		raise RuntimeError("Network connection failed")
	else:
		print("Connected")
		print("ip = " + wlan.ifconfig()[0])


async def serve_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
	"""
	Simple async web server.
	"""
	http_header = ""
	http_content = ""

	led_value = {False: "off", True: "on"}

	print("Client connected")

	#request_line = await reader.readline()
	request_line = b""
	try:
		request_line = await asyncio.wait_for(reader.readline(), 1.0)
	except asyncio.TimeoutError:
		print("TimeOut")

	if (request_line != b""):
	
		request = str(request_line)

		print("Request from: " + writer.get_extra_info('peername')[0])
		print("Request: " + request)
		
		# We skip all HTTP request headers.
		# To avoid malformed requests, we wait for a maximum time.
		ticksStart = time.ticks_ms()
		while ((await reader.readline() != b"\r\n") and (time.ticks_diff(time.ticks_ms(), ticksStart) < 250)):
			pass
		
		url=request.split(" ")[1]

		if (url == "/on"):
			print("LED on")
			led_external.on()
			http_header += "HTTP/1.0 303 OK\r\n"
			http_header += "Location: /\r\n"

		elif (url == "/off"):
			print("LED off")
			led_external.off()
			http_header += "HTTP/1.0 303 OK\r\n"
			http_header += "Location: /\r\n"

		else:
			http_header += "HTTP/1.0 200 OK\r\n"
			http_header += "Content-type: text/html\r\n"

			val = bool(led_external.value())
			http_content += template.replace("{status}", led_value[val])

		response = http_header + "\r\n" + http_content

		writer.write(response)
		
		await writer.drain()
		await writer.wait_closed()
		print("Client disconnected")


async def main():
	global template

	print("Connecting to Network...")
	connect_to_network()

	print("Read template...")
	with open(cfg.SERVER_TEMPLATE_FILENAME, "r") as file:
		template = file.read()

	print("Setting up webserver...")
	asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", cfg.SERVER_PORT))

	print("Enable heartbeat...")
	while True:
		print("heartbeat")
		led_onboard.on()
		await asyncio.sleep(0.25)
		led_onboard.off()
		await asyncio.sleep(4.75)


if __name__ == '__main__':
	try:
		asyncio.run(main())
	finally:
		asyncio.new_event_loop()
