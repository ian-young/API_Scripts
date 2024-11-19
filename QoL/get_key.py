import requests


def get_api_token(key):
    headers = {"accept": "application/json", "x-api-key": key}

    response = requests.post(
        "https://api.verkada.com/token", headers=headers, timeout=5
    )
    return response.json()["token"]
