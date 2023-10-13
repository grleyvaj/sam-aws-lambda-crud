import boto3
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

dynamodb_table_name = 'book'
dynamodb_client = boto3.resource('dynamodb')
table = dynamodb_client.Table(dynamodb_table_name)


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)


@app.post("/books")
@tracer.capture_method
def create_book_event():
    payload = app.current_event.json_body
    current = (datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    table.put_item(
        Item={
            'id': payload['id'],
            'title': payload['title'],
            'description': payload['description'],
            'published': payload['published'],
            'updatedAt': current,
            'createdAt': current
        }
    )

    return {"book": payload}, 201


@app.get("/books")
@tracer.capture_method
def get_books_event():
    response = table.scan()
    result = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        result.extend(response['Items'])

    return {"books": result}, 200


@app.get("/books/<book_id>")
@tracer.capture_method
def show_book_event(book_id: str):

    result = table.get_item(Key={'id': book_id})
    logger.info(">> result get item %s", result)

    if "Item" in result:
        return {"book": result['Item']}, 200
    else:
        return {"message": "Item not found"}, 404
