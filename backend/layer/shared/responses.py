import json


def json_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def success(body, status_code=200):
    return json_response(status_code, body)


def error(message, status_code=500):
    return json_response(status_code, {"error": message})
