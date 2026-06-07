def readConfig(filename):
    import json

    with open(filename, "r") as file:
        for line in file:
            str = line.strip().split(': ')
            if str[0] == "Type":
                type = str[1]
            elif str[0] == "Location":
                location = str[1]
        data = {
            "sensorType": type,
            "locationName": location
        }
    return data