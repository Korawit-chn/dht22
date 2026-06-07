def networkSearch(filename, port, route):
    import requests

    with open(filename, "r") as file:
        for line in file:
            url = f"http://{line.strip()}:{port}{route}"

            try:
                r = requests.get(url, timeout=5)

                if r.status_code == 200:
                    return url

            except requests.RequestException:
                pass

    return None