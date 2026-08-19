import json
import os

import anthropic
from queries import get_dietary_tags, get_saved_recipes

from shared.db import get_connection

CLAUDE_MODEL = "claude-sonnet-5"


def build_prompt(preferences: dict, dietary_tags: list[str], saved_recipes: list[dict]) -> str:
    days = preferences["days"]
    meals_per_day = preferences["mealsPerDay"]
    dietary_line = (
        f"Dietary constraints (must follow strictly): {', '.join(dietary_tags)}.\n"
        if dietary_tags
        else ""
    )
    saved_titles = [r["title"] for r in saved_recipes]
    inspiration_line = (
        f"For style inspiration only (not hard requirements), the user has previously "
        f"saved: {', '.join(saved_titles)}.\n"
        if saved_titles
        else ""
    )
    return (
        f"Generate a {days}-day meal plan with {meals_per_day} meals per day.\n"
        f"{dietary_line}"
        f"{inspiration_line}"
        "Respond with ONLY valid JSON (no markdown fences, no commentary) in exactly "
        "this shape:\n"
        '{"days": [{"day": 1, "meals": [{"recipeId": null, "name": "string", '
        '"notes": "string"}]}]}\n'
        f'There must be exactly {days} entries in "days", each with exactly '
        f'{meals_per_day} entries in "meals". "recipeId" is always null.'
    )


def _fetch_job(cursor, job_id: str) -> tuple[int, dict]:
    cursor.execute(
        "SELECT user_id, request_preferences FROM mealplan_job WHERE id = %s",
        (job_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"no mealplan_job found for id {job_id}")
    return row["user_id"], json.loads(row["request_preferences"])


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
                user_id, preferences = _fetch_job(cursor, job_id)

            dietary_tags = get_dietary_tags(conn, user_id)
            saved_recipes = get_saved_recipes(conn, user_id)

            plan = _call_claude(build_prompt(preferences, dietary_tags, saved_recipes))

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