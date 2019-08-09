import boto3
import os
import aws_deep_sense_spoken_data_collection_framework.utils as utils

test_data_directory = os.path.join(os.path.dirname(__file__), '..', 'test-data')
config_test_path = os.path.join(test_data_directory, 'aws_config_test')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_test_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_test_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_test_path)


def create_mock_dynamodb_collection_session_table():
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION_NAME)
    response = dynamodb_client.create_table(
        TableName=utils.COLLECTION_REQUEST_DYNAMODB_TABLE,
        KeySchema=[
            {
                'AttributeName': utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY,
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY,
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10,
        },
        GlobalSecondaryIndexes=[
            {
                'IndexName': utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX,
                'KeySchema': [
                    {
                        'AttributeName': utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY,
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL',
                },
            },
        ],
    )


def create_mock_dynamodb_user_account_table():
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION_NAME)
    response = dynamodb_client.create_table(
        TableName=utils.USER_ACCOUNT_DYNAMODB_TABLE,
        KeySchema=[
            {
                'AttributeName': utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY,
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY,
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10,
        },
    )


def create_mock_dynamodb_collection_bot_table():
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION_NAME)
    response = dynamodb_client.create_table(
        TableName='collectionBot',
        KeySchema=[
            {
                'AttributeName': 'bot',
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'bot',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10,
        },
    )

def create_mock_dynamodb_queue_pool_table():
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION_NAME)
    response = dynamodb_client.create_table(
        TableName='connectQueuePool',
        KeySchema=[
            {
                'AttributeName': 'queueNumber',
                'KeyType': 'HASH'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'queueNumber',
                'AttributeType': 'N'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10,
        },
    )