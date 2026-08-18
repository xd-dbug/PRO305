
def get_saved_recipes(conn, user_id) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT r.title, r.rating_avg FROM saved_recipe sr "
            "JOIN recipes r on r.id = sr.recipe_id "
            "WHERE sr.user_id = %s ",
            (user_id,),
        )
        return cursor.fetchall()

def get_dietary_tags(conn, user_id) -> list[str]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT dt.name FROM user_dietary_tag udt "
            "JOIN dietary_tag dt ON dt.id = udt.dietary_tag_id "
            "WHERE udt.user_id = %s",
            (user_id,),
        )
        return [row["name"] for row in cursor.fetchall()]