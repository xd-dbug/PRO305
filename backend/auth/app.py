import os

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError

from auth_service import issue_token, verify_password
from shared.db import get_connection

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="http://localhost:5173"))


@app.post("/auth/login")
def login():
    body = app.current_event.json_body or {}
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise BadRequestError("email and password are required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, role FROM users WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    if row is None or not verify_password(password, row["password_hash"]):
        raise UnauthorizedError("invalid email or password")

    token = issue_token(row["id"], row["email"], row["role"], secret=os.environ["JWT_SECRET"])
    return {"token": token}


def lambda_handler(event, context):
    return app.resolve(event, context)
