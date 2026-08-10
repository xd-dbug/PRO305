from shared.responses import success


def lambda_handler(event, context):
    return success({"status": "ok"})
