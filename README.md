# Link
https://github.com/Omelettae/sp_dashboard

# dht22
```
sudo apt update
sudo apt install python3-pip python3-venv
```
```
python3 -m venv ~/venv
source ~/venv/bin/activate
```

Inside venv
```
pip3 install adafruit-circuitpython-dht
pip install requests
```

config.txt example 
```
Type: DHT22
Location: Outside Dome 1
GPIO: D17
```

networkList.txt example
```
10.230.146.87
192.168.1.100
192.168.1.130
```
