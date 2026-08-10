from shared.db import get_connection
from shared.responses import error, success


def lambda_handler(event, context):
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        finally:
            conn.close()
    except Exception as exc:
        return error(f"RDS connection failed: {exc}", status_code=500)
    return success({"rds_connection": "ok"})
