import json

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response

app = APIGatewayRestResolver()

_MOCK_RECIPE = {
    "id": 1,
    "title": "Placeholder Recipe",
    "description": "Stub data — no DB wired up yet",
    "ingredients": ["stub ingredient"],
    "steps": ["stub step"],
    "author_id": 1,
    "rating_avg": 0,
}


@app.get("/recipes")
def list_recipes():
    return {"recipes": [_MOCK_RECIPE]}


@app.get("/recipes/<recipe_id>")
def get_recipe(recipe_id: str):
    return {**_MOCK_RECIPE, "id": int(recipe_id)}


@app.post("/recipes")
def create_recipe():
    body = app.current_event.json_body or {}
    return Response(
        status_code=201,
        content_type="application/json",
        body=json.dumps({**_MOCK_RECIPE, **body, "id": 999}),
    )


@app.put("/recipes/<recipe_id>")
def update_recipe(recipe_id: str):
    body = app.current_event.json_body or {}
    return {**_MOCK_RECIPE, **body, "id": int(recipe_id)}


@app.delete("/recipes/<recipe_id>")
def delete_recipe(recipe_id: str):
    return {"deleted": True, "id": int(recipe_id)}


@app.post("/recipes/<recipe_id>/rate")
def rate_recipe(recipe_id: str):
    body = app.current_event.json_body or {}
    return {"recipe_id": int(recipe_id), "rating": body.get("rating"), "rating_avg": 0}


@app.post("/recipes/<recipe_id>/save")
def save_recipe(recipe_id: str):
    return {"recipe_id": int(recipe_id), "saved": True}


def lambda_handler(event, context):
    return app.resolve(event, context)
