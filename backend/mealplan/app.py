def lambda_handler(event, context):
    records = event.get("Records", [])
    print(f"Received {len(records)} message(s) from the mealplan queue")
    for record in records:
        print(f"  body: {record.get('body')}")
    return {"processed": len(records)}
