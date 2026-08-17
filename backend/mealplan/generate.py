import json
import os
import uuid

import boto3
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response
from aws_lambda_powertools.event_handler.exceptions import BadRequestError

from shared.db import get_connection
from shared.auth_middleware import require_auth

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="http://localhost:5173"))


def _validate_preferences(body: dict) -> dict:
    preferences = (body or {}).get("preferences")
    if not isinstance(preferences, dict):
        raise BadRequestError("preferences is required")
    days = preferences.get("days")
    meals_per_day = preferences.get("mealsPerDay")
    if not isinstance(days, int) or days <= 0:
        raise BadRequestError("preferences.days must be a positive integer")
    if not isinstance(meals_per_day, int) or meals_per_day <= 0:
        raise BadRequestError("preferences.mealsPerDay must be a positive integer")
    return {"days": days, "mealsPerDay": meals_per_day}


@app.post("/mealplan/generate")
def generate():
    user = require_auth(app)
    preferences = _validate_preferences(app.current_event.json_body)

    job_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO mealplan_job (id, user_id, status, request_preferences) "
                "VALUES (%s, %s, 'pending', %s)",
                (job_id, user["sub"], json.dumps(preferences)),
            )
        conn.commit()
    finally:
        conn.close()

    sqs = boto3.client("sqs")
    sqs.send_message(
        QueueUrl=os.environ["MEALPLAN_QUEUE_URL"],
        MessageBody=json.dumps({"jobId": job_id}),
    )

    return Response(
        status_code=202,
        content_type="application/json",
        body=json.dumps({"jobId": job_id, "status": "pending"}),
    )


def lambda_handler(event, context):
    return app.resolve(event, context)