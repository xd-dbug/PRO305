import json
import os

import anthropic

from shared.db import get_connection

CLAUDE_MODEL = "claude-sonnet-5"


def build_prompt(preferences: dict) -> str:
    days = preferences["days"]
    meals_per_day = preferences["mealsPerDay"]
    return (
        f"Generate a {days}-day meal plan with {meals_per_day} meals per day.\n"
        "Respond with ONLY valid JSON (no markdown fences, no commentary) in exactly "
        "this shape:\n"
        '{"days": [{"day": 1, "meals": [{"recipeId": null, "name": "string", '
        '"notes": "string"}]}]}\n'
        f'There must be exactly {days} entries in "days", each with exactly '
        f'{meals_per_day} entries in "meals". "recipeId" is always null.'
    )


def _fetch_preferences(cursor, job_id: str) -> dict:
    cursor.execute(
        "SELECT request_preferences FROM mealplan_job WHERE id = %s",
        (job_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"no mealplan_job found for id {job_id}")
    return json.loads(row["request_preferences"])


def _call_claude(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    plan = json.loads(text)
    if not isinstance(plan, dict) or not isinstance(plan.get("days"), list):
        raise ValueError("Claude response did not match the expected generated_plan shape")
    return plan


def _process_record(record):
    body = json.loads(record["body"])
    job_id = body["jobId"]

    conn = get_connection()
    try:
        try:
            with conn.cursor() as cursor:
                preferences = _fetch_preferences(cursor, job_id)

            plan = _call_claude(build_prompt(preferences))

            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE mealplan_job SET status = 'complete', generated_plan = %s "
                    "WHERE id = %s",
                    (json.dumps(plan), job_id),
                )
            conn.commit()
        except Exception as e:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE mealplan_job SET status = 'failed', error_message = %s "
                    "WHERE id = %s",
                    (str(e), job_id),
                )
            conn.commit()
            raise
    finally:
        conn.close()


def lambda_handler(event, context):
    records = event.get("Records", [])
    for record in records:
        _process_record(record)
    return {"processed": len(records)}