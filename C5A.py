import serial
import time
import math
import requests
from datetime import datetime


def modbus_crc(data: bytes):
	crc = 0xFFFF
	for b in data:
		crc ^= b
		for _ in range(8):
			if crc & 1:
				crc = (crc >> 1) ^ 0xA001
			else:
				crc >>= 1
	return crc.to_bytes(2, 'little')
	
def temp_convert(data: bytes):
	binary = format(int(data, 16), '016b')
	sign = binary[1]
	
	if sign == '1':
		value = -((int(''.join('1' if x=='0' else '0' for x in binary), 2) + 1))
	else:
		value = int(binary, 2)
		
	return value
	
try:	
	ser = serial.Serial(
		port='/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0',
		baudrate=9600,
		bytesize=8,
		parity="N",
		stopbits=1,
		timeout=2
	)

	url = "http://192.168.1.100:5000/"
	server_connect = False
	try:
		r_test = requests.get(url, timeout = 5)

		if r_test.status_code == 200:	
			server_connect = True
			print("URL connected")
			url = "http://192.168.1.100:5000/api/getDataC5A"
			
		print(r_test.status_code, r_test)

	except requests.exceptions.Timeout:
		print("URL not connected")


	payload = bytes([0x01,0x03,0x00,0x00,0x00,0x05])
	frame = payload + modbus_crc(payload)

	print("Send: ", frame.hex(' '))
	print("---------------------------------------------------")

	while True:
		try:
			ser.write(frame)
			timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			time.sleep(1.1)
			print("Time:",timestamp)
			response = ser.read(20)
			#print("Receive:", response.hex(' '))

			data = response[3:11]

			wind_speed = int.from_bytes(data[0:2], 'big') * 0.01
			# print("yes")
			wind_direction = int.from_bytes(data[2:4], 'big')
			# print("yes")
			temperature = temp_convert(data[4:6].hex().upper()) * 0.1
			# print("yes")
			humidity = int.from_bytes(data[6:8], 'big') * 0.1
			# print("yes")
			vpd = 0.6108 * math.exp((17.27*temperature)/(temperature+237.3)) * (1-(humidity/100))
				
			queryData = {
				"sensorID": 4,
				"windSpeed": wind_speed,
				"windDirection": wind_direction,
				"temperature": temperature,
				"humidity":humidity,
				"VPD": vpd,
				"time": timestamp
			}
				
			if server_connect:
			
				r = requests.post(url, json=queryData, timeout=5) 
				if (r.status_code != 200):
					print(r)
			print(f"Wind Speed: {wind_speed:.2f} m/s")
			print(f"Wind Direction: {wind_direction}\u00B0")
			print(f"Temp: {temperature:.1f}°C Humidity: {humidity:.1f}% VPD: {vpd:.1f}kPa")
			print("---------------------------------------------------")
			
		except Exception as e:
			print("Error Occur ",e)
			
except KeyboardInterrupt:
	print("Program End")



