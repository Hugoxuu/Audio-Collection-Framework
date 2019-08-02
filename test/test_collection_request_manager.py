# test_collection_request_manager.py: Unit test for the framework

import unittest
import os
import boto3
import mock
from moto import mock_dynamodb2
from aws_deep_sense_spoken_data_collection_framework.collection_request_manager import CollectionRequestManager
import aws_deep_sense_spoken_data_collection_framework.utils as utils

# Set up default session for mocking AWS PYTHON SDK (boto3)
boto3.setup_default_session()

# Retrieve AWS Access Key
test_data_directory = os.path.join(os.path.dirname(__file__), '..', 'test-data')
config_test_path = os.path.join(test_data_directory, 'aws_config_test')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_test_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_test_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_test_path)

# Create Class Objects
collection_request_manager = CollectionRequestManager(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                                      CALL_RECORDINGS_BUCKET_NAME)

collection_request_manager_method_prefix_list = ['aws_deep_sense_spoken_data_collection_framework',
                                                 'collection_request_manager', 'CollectionRequestManager']
collection_request_manager_method_prefix = '.'.join(collection_request_manager_method_prefix_list)


class TestCollectionRequestManage(unittest.TestCase):
    def test_is_category_choice_valid(self):
        # Test 1
        expected_response = False
        actual_response = collection_request_manager.is_number_choice_valid('0', 1)
        self.assertEqual(actual_response, expected_response)
        # Test 2
        expected_response = False
        actual_response = collection_request_manager.is_number_choice_valid('2', 1)
        self.assertEqual(actual_response, expected_response)
        # Test 3
        expected_response = True
        actual_response = collection_request_manager.is_number_choice_valid('1', 1)
        self.assertEqual(actual_response, expected_response)
        # Test 4
        expected_response = False
        actual_response = collection_request_manager.is_number_choice_valid('1abc', 100)
        self.assertEqual(actual_response, expected_response)

    @mock.patch('builtins.input', return_value='10')
    def test_ask_collection_goal(self, input):
        expected_response = 10
        actual_response = collection_request_manager.ask_collection_goal()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_change_collection_status_given_info(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        test_collection_pin = '123456'
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: test_collection_pin, 'collectionStatus': 'START'}
            batch.put_item(Item=user_item)

        # test 1
        expected_response = 'PAUSE'
        collection_request_manager.change_collection_status_given_info(test_collection_pin, 'PAUSE')
        session = table.get_item(Key={"collectionPIN": test_collection_pin})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']['collectionStatus']
        self.assertEqual(actual_response, expected_response)

        # test 2
        expected_response = 'START'
        collection_request_manager.change_collection_status_given_info(test_collection_pin, 'START')
        session = table.get_item(Key={"collectionPIN": test_collection_pin})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']['collectionStatus']
        self.assertEqual(actual_response, expected_response)

        # test 3
        expected_response = 'START'
        collection_request_manager.change_collection_status_given_info(test_collection_pin, 'invalid_collection_status')
        session = table.get_item(Key={"collectionPIN": test_collection_pin})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']['collectionStatus']
        self.assertEqual(actual_response, expected_response)

        # test 4
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: test_collection_pin, 'collectionStatus': 'STOP'}
            batch.put_item(Item=user_item)

        expected_response = 'STOP'
        collection_request_manager.change_collection_status_given_info(test_collection_pin, 'START')
        session = table.get_item(Key={"collectionPIN": test_collection_pin})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']['collectionStatus']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('aws_deep_sense_spoken_data_collection_framework.utils.ask_collection_pin', return_value='123456')
    @mock.patch('builtins.input', return_value='PAUSE')
    def test_change_collection_status(self, input1, input2):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        test_collection_pin = '123456'
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: test_collection_pin, 'collectionStatus': 'START'}
            batch.put_item(Item=user_item)

        expected_response = 'PAUSE'
        collection_request_manager.change_collection_status()
        session = table.get_item(Key={"collectionPIN": test_collection_pin})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']['collectionStatus']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_list_collect_requests(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)

        with table.batch_writer() as batch:
            user_item_1 = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456', 'conversationPIN': '987654',
                           'mode': 'human', 'contactIDs': [], 'collectionGoal': 12, 'collectionStatus': 'START',
                           'collectionCategory': 'travel'}
            batch.put_item(Item=user_item_1)

        expected_response = [user_item_1]
        actual_response = collection_request_manager.list_collect_requests()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_collection_request_given_pin(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)

        # test 1
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456', 'conversationPIN': '987654',
                         'mode': 'human', 'contactIDs': [], 'collectionGoal': 12, 'collectionStatus': 'START',
                         'collectionCategory': 'travel'}
            batch.put_item(Item=user_item)

        expected_response = {'collection_pin': '123456', 'conversation_pin': '987654', 'mode': 'human',
                             'collection_info': 'travel', 'contact_ids': [], 'collection_goal': 12,
                             'collectionStatus': 'START'}
        actual_response = collection_request_manager.get_collection_request_given_pin('123456')
        self.assertEqual(actual_response, expected_response)

        # test 2
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '987654', 'conversationPIN': '123456',
                         'mode': 'bot', 'contactIDs': ['123'], 'collectionGoal': 1, 'collectionStatus': 'PAUSE',
                         'collectionBot': 'OrderFlowers'}
            batch.put_item(Item=user_item)

        expected_response = {'collection_pin': '987654', 'conversation_pin': '123456', 'mode': 'bot',
                             'collection_info': 'OrderFlowers', 'contact_ids': ['123'], 'collection_goal': 1,
                             'collectionStatus': 'PAUSE'}
        actual_response = collection_request_manager.get_collection_request_given_pin('987654')
        self.assertEqual(actual_response, expected_response)

        # test 3
        expected_response = True
        response = collection_request_manager.get_collection_request_given_pin('invalid_collection_pin')
        actual_response = 'error' in response
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_save2db(self):
        self.create_mock_dynamodb_collection_session_table()

        # test 1
        collection_pin = '123456'
        conversation_pin = '987654'
        mode = 'human'
        collection_choice = {'collectionCategory': 'finance', 'queueArn': 'test_queue_arn'}
        collection_goal = 10
        collection_status = 'START'
        collection_request_manager.save2db(collection_pin, conversation_pin, mode, collection_choice, collection_goal,
                                           collection_status)

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'human', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START',
                             'collectionCategory': 'finance', 'queueArn': 'test_queue_arn'}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

        # test 2
        collection_pin = '987654'
        conversation_pin = '123456'
        mode = 'bot'
        collection_choice = {'collectionBot': 'OrderFlowers'}
        collection_goal = 1
        collection_status = 'START'
        collection_request_manager.save2db(collection_pin, conversation_pin, mode, collection_choice, collection_goal,
                                           collection_status)

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': '987654', 'conversationPIN': '123456', 'mode': 'bot', 'contactIDs': [],
                             'collectionGoal': 1, 'collectionStatus': 'START',
                             'collectionBot': 'OrderFlowers'}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_available_collection_category(self):
        self.create_mock_dynamodb_collection_category_table()
        self.create_mock_dynamodb_collection_bot_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        category_table = dynamodb_resource.Table('collectionCategory')
        with category_table.batch_writer() as batch:
            finance_category = {'category': 'finance', 'queueArn': 'test_finance_queue_arn'}
            batch.put_item(Item=finance_category)
            travel_category = {'category': 'travel', 'queueArn': 'test_travel_queue_arn'}
            batch.put_item(Item=travel_category)
            enterprise_category = {'category': 'enterprise', 'queueArn': 'test_enterprise_queue_arn'}
            batch.put_item(Item=enterprise_category)

        bot_table = dynamodb_resource.Table('collectionBot')
        with bot_table.batch_writer() as batch:
            order_flowers_bot = {'bot': 'OrderFlowers'}
            batch.put_item(Item=order_flowers_bot)
            book_trip_bot = {'bot': 'BookTrip'}
            batch.put_item(Item=book_trip_bot)

        actual_category, actual_bot = collection_request_manager.get_available_collection_category()
        self.assertTrue(finance_category in actual_category)
        self.assertTrue(travel_category in actual_category)
        self.assertTrue(enterprise_category in actual_category)
        self.assertTrue(order_flowers_bot in actual_bot)
        self.assertTrue(book_trip_bot in actual_bot)

    @mock_dynamodb2
    @mock.patch('builtins.input', return_value='1')
    def test_ask_collection_category(self, input):
        self.create_mock_dynamodb_collection_category_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table('collectionCategory')
        with table.batch_writer() as batch:
            finance_category = {'category': 'finance', 'queueArn': 'test_finance_queueArn'}
            batch.put_item(Item=finance_category)
            travel_category = {'category': 'travel', 'queueArn': 'test_travel_queueArn'}
            batch.put_item(Item=travel_category)
            enterprise_category = {'category': 'enterprise', 'queueArn': 'test_enterprise_queueArn'}
            batch.put_item(Item=enterprise_category)

        expected_response_1 = {'collectionCategory': 'finance', 'queueArn': 'test_finance_queueArn'}
        expected_response_2 = {'collectionCategory': 'travel', 'queueArn': 'test_travel_queueArn'}
        expected_response_3 = {'collectionCategory': 'enterprise', 'queueArn': 'test_enterprise_queueArn'}
        actual_response = collection_request_manager.ask_collection_category()
        print(actual_response)
        self.assertTrue(
            actual_response == expected_response_1 or actual_response == expected_response_2 or actual_response == expected_response_3)

    @mock_dynamodb2
    @mock.patch('builtins.input', return_value='1')
    def test_ask_collection_bot(self, input):
        self.create_mock_dynamodb_collection_bot_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table('collectionBot')
        with table.batch_writer() as batch:
            user_item = {'bot': 'OrderFlowers'}
            batch.put_item(Item=user_item)
            user_item = {'bot': 'BookTrip'}
            batch.put_item(Item=user_item)

        expected_response_1 = {'collectionBot': 'OrderFlowers'}
        expected_response_2 = {'collectionBot': 'BookTrip'}
        actual_response = collection_request_manager.ask_collection_bot()
        self.assertTrue(actual_response == expected_response_1 or actual_response == expected_response_2)

    def test_ask_collection_mode(self):
        # test 1
        with mock.patch('builtins.input') as input_mock:
            input_mock.return_value = '1'
            expected_response = True
            actual_response = collection_request_manager.ask_collection_mode()
            self.assertEqual(actual_response, expected_response)

        # test 2
        with mock.patch('builtins.input') as input_mock:
            input_mock.return_value = '2'
            expected_response = False
            actual_response = collection_request_manager.ask_collection_mode()
            self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_generate_collection_pin(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        expected_num_collection_session = 1000
        for i in range(expected_num_collection_session):
            collection_pin = collection_request_manager.generate_collection_pin()
            with table.batch_writer() as batch:
                user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin,
                             utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: collection_pin}
                batch.put_item(Item=user_item)
        actual_num_collection_session = table.item_count
        self.assertEqual(actual_num_collection_session, expected_num_collection_session)

    @mock_dynamodb2
    def test_generate_conversation_pin(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        expected_num_collection_session = 1000
        for i in range(expected_num_collection_session):
            conversation_pin = collection_request_manager.generate_conversation_pin()
            with table.batch_writer() as batch:
                user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: conversation_pin,
                             utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: conversation_pin}
                batch.put_item(Item=user_item)
        actual_num_collection_session = table.item_count
        self.assertEqual(actual_num_collection_session, expected_num_collection_session)

    @mock_dynamodb2
    def test_generate_collection_request_given_info(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        # test 1
        self.create_mock_dynamodb_collection_category_table()
        table = dynamodb_resource.Table('collectionCategory')
        with table.batch_writer() as batch:
            finance_category = {'category': 'finance', 'queueArn': 'test_finance_queueArn'}
            batch.put_item(Item=finance_category)

        mode = 'human'
        collection_category = 'finance'
        collection_goal = 2
        collection_pin, conversation_pin = collection_request_manager.generate_collection_request_given_info(mode,
                                                                                                             collection_category,
                                                                                                             collection_goal)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': collection_pin, 'conversationPIN': conversation_pin, 'mode': mode,
                             'contactIDs': [],
                             'collectionGoal': collection_goal, 'collectionStatus': 'START',
                             'collectionCategory': collection_category,
                             'queueArn': 'test_finance_queueArn'}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

        # test 2
        self.create_mock_dynamodb_collection_bot_table()
        table = dynamodb_resource.Table('collectionBot')
        with table.batch_writer() as batch:
            order_flowers_bot = {'bot': 'OrderFlowers'}
            batch.put_item(Item=order_flowers_bot)

        mode = 'bot'
        collection_category = 'OrderFlowers'
        collection_goal = 2
        collection_pin, conversation_pin = collection_request_manager.generate_collection_request_given_info(mode,
                                                                                                             collection_category,
                                                                                                             collection_goal)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': collection_pin, 'conversationPIN': conversation_pin, 'mode': mode,
                             'contactIDs': [], 'collectionGoal': collection_goal, 'collectionStatus': 'START',
                             'collectionBot': collection_category}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('{}.generate_collection_pin'.format(collection_request_manager_method_prefix), return_value='123456')
    @mock.patch('{}.generate_conversation_pin'.format(collection_request_manager_method_prefix), return_value='987654')
    @mock.patch('{}.ask_collection_mode'.format(collection_request_manager_method_prefix), return_value=True)
    @mock.patch('{}.ask_collection_goal'.format(collection_request_manager_method_prefix), return_value=10)
    @mock.patch('{}.ask_collection_category'.format(collection_request_manager_method_prefix),
                return_value={'collectionCategory': 'finance', 'queueArn': 'test_finance_queueArn'})
    def test_generate_collection_request_test1(self, input1, input2, input3, input4, input5):
        self.create_mock_dynamodb_collection_session_table()
        collection_request_manager.generate_collect_request()
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'human', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START',
                             'collectionCategory': 'finance', 'queueArn': 'test_finance_queueArn'}

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456'})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('{}.generate_collection_pin'.format(collection_request_manager_method_prefix), return_value='123456')
    @mock.patch('{}.generate_conversation_pin'.format(collection_request_manager_method_prefix), return_value='987654')
    @mock.patch('{}.ask_collection_mode'.format(collection_request_manager_method_prefix), return_value=False)
    @mock.patch('{}.ask_collection_goal'.format(collection_request_manager_method_prefix), return_value=10)
    @mock.patch('{}.ask_collection_bot'.format(collection_request_manager_method_prefix),
                return_value={'collectionBot': 'OrderFlowers'})
    def test_generate_collection_request_test2(self, input1, input2, input3, input4, input5):
        self.create_mock_dynamodb_collection_session_table()
        collection_request_manager.generate_collect_request()
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'bot', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START',
                             'collectionBot': 'OrderFlowers'}

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456'})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    def create_mock_dynamodb_collection_session_table(self):
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

    def create_mock_dynamodb_collection_category_table(self):
        dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION_NAME)
        response = dynamodb_client.create_table(
            TableName='collectionCategory',
            KeySchema=[
                {
                    'AttributeName': 'category',
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'category',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'queueArn',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10,
            },
        )

    def create_mock_dynamodb_collection_bot_table(self):
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


if __name__ == '__main__':
    unittest.main()
