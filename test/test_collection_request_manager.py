# test_collection_request_manager.py: Unit test for the framework

import unittest
import os
import boto3
import mock
from moto import mock_dynamodb2
from aws_deep_sense_spoken_data_collection_framework.collection_request_manager import CollectionRequestManager
import aws_deep_sense_spoken_data_collection_framework.utils as utils
import unittest_helper_methods as helper

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
    @mock.patch('builtins.input', return_value='10')
    def test_ask_collection_goal(self, input):
        expected_response = 10
        actual_response = collection_request_manager.ask_collection_goal()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_change_collection_status_given_info(self):
        helper.create_mock_dynamodb_collection_session_table()
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
        helper.create_mock_dynamodb_collection_session_table()
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
        helper.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)

        with table.batch_writer() as batch:
            user_item_1 = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456',
                           utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: '987654', 'mode': 'human',
                           'contactIDs': [], 'collectionGoal': 1, 'collectionStatus': 'START',
                           'collectionName': 'test_collection_name',
                           'routingInfo': {'queueNumber': '1', 'queueID': 'test_queue_id',
                                           'routingProfileID': 'test_routing_profile_id'}}
            batch.put_item(Item=user_item_1)

        expected_response = [user_item_1]
        actual_response = collection_request_manager.list_collect_requests()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_collection_request_given_pin(self):
        helper.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)

        # test 1
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456',
                         utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: '987654', 'mode': 'human',
                         'contactIDs': [], 'collectionGoal': 1, 'collectionStatus': 'START',
                         'collectionName': 'test_collection_name',
                         'routingInfo': {'queueNumber': '1', 'queueID': 'test_queue_id',
                                         'routingProfileID': 'test_routing_profile_id'}}
            batch.put_item(Item=user_item)

        expected_response = {'collection_pin': '123456', 'conversation_pin': '987654', 'mode': 'human',
                             'contact_ids': [], 'collection_goal': 1, 'collection_status': 'START',
                             'collection_name': 'test_collection_name', 'collection_info': None}
        actual_response = collection_request_manager.get_collection_request_given_pin('123456')
        self.assertEqual(actual_response, expected_response)

        # test 2
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '987654', 'conversationPIN': '123456',
                         'mode': 'bot', 'contactIDs': ['123'], 'collectionGoal': 1, 'collectionStatus': 'PAUSE',
                         'collectionBot': 'OrderFlowers', 'collectionName': 'test_collection_name'}
            batch.put_item(Item=user_item)

        expected_response = {'collection_pin': '987654', 'conversation_pin': '123456', 'mode': 'bot',
                             'collection_info': 'OrderFlowers', 'contact_ids': ['123'], 'collection_goal': 1,
                             'collection_status': 'PAUSE', 'collection_name': 'test_collection_name'}
        actual_response = collection_request_manager.get_collection_request_given_pin('987654')
        self.assertEqual(actual_response, expected_response)

        # test 3
        expected_response = True
        response = collection_request_manager.get_collection_request_given_pin('invalid_collection_pin')
        actual_response = 'error' in response
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_save2db(self):
        helper.create_mock_dynamodb_collection_session_table()

        # test 1
        collection_pin = '123456'
        conversation_pin = '987654'
        mode = 'human'
        collection_info = {'routingInfo': {}}
        collection_goal = 10
        collection_status = 'START'
        collection_name = 'test_collection_name'
        collection_request_manager.save2db(collection_pin, conversation_pin, mode, collection_info, collection_goal,
                                           collection_status, collection_name)

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'human', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START', 'collectionName': collection_name,
                             'routingInfo': {}}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

        # test 2
        collection_pin = '987654'
        conversation_pin = '123456'
        mode = 'bot'
        collection_info = {'collectionBot': 'OrderFlowers'}
        collection_goal = 1
        collection_status = 'START'
        collection_name = 'test_collection_name'
        collection_request_manager.save2db(collection_pin, conversation_pin, mode, collection_info, collection_goal,
                                           collection_status, collection_name)

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': '987654', 'conversationPIN': '123456', 'mode': 'bot', 'contactIDs': [],
                             'collectionGoal': 1, 'collectionStatus': 'START',
                             'collectionBot': 'OrderFlowers', 'collectionName': collection_name}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('builtins.input', return_value='1')
    def test_ask_collection_bot(self, input):
        helper.create_mock_dynamodb_collection_bot_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table('collectionBot')
        with table.batch_writer() as batch:
            user_item = {'bot': 'OrderFlowers'}
            batch.put_item(Item=user_item)
            user_item = {'bot': 'BookTrip'}
            batch.put_item(Item=user_item)

        expected_response_1 = 'OrderFlowers'
        expected_response_2 = 'BookTrip'
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
        helper.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        expected_num_collection_session = 100
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
        helper.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        expected_num_collection_session = 100
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
        helper.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        # test 1
        helper.create_mock_dynamodb_queue_pool_table()
        table = dynamodb_resource.Table('connectQueuePool')
        with table.batch_writer() as batch:
            routing_info = {'queueNumber': '1', 'queueID': 'test_queue_id',
                            'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info)

        mode = 'human'
        collection_goal = 1
        collection_name = 'test_collection_name'
        collection_pin, conversation_pin = collection_request_manager.generate_collection_request_given_info(mode, None,
                                                                                                             collection_goal,
                                                                                                             collection_name)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin,
                             utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: conversation_pin, 'mode': 'human',
                             'contactIDs': [], 'collectionGoal': 1, 'collectionStatus': 'START',
                             'collectionName': 'test_collection_name',
                             'routingInfo': {'queueNumber': '1', 'queueID': 'test_queue_id',
                                             'routingProfileID': 'test_routing_profile_id'}}

        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

        # test 2
        helper.create_mock_dynamodb_collection_bot_table()
        table = dynamodb_resource.Table('collectionBot')
        with table.batch_writer() as batch:
            order_flowers_bot = {'bot': 'OrderFlowers'}
            batch.put_item(Item=order_flowers_bot)

        mode = 'bot'
        collection_bot = 'OrderFlowers'
        collection_goal = 2
        collection_name = 'test_collection_name'
        collection_pin, conversation_pin = collection_request_manager.generate_collection_request_given_info(mode,
                                                                                                             collection_bot,
                                                                                                             collection_goal,
                                                                                                             collection_name)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        if 'Item' not in session:
            raise AssertionError
        expected_response = {'collectionPIN': collection_pin, 'conversationPIN': conversation_pin, 'mode': mode,
                             'contactIDs': [], 'collectionGoal': collection_goal, 'collectionStatus': 'START',
                             'collectionBot': collection_bot, 'collectionName': 'test_collection_name'}
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('{}.generate_collection_pin'.format(collection_request_manager_method_prefix), return_value='123456')
    @mock.patch('{}.generate_conversation_pin'.format(collection_request_manager_method_prefix), return_value='987654')
    @mock.patch('{}.ask_collection_name'.format(collection_request_manager_method_prefix), return_value='name')
    @mock.patch('{}.ask_collection_mode'.format(collection_request_manager_method_prefix), return_value=True)
    @mock.patch('{}.ask_collection_goal'.format(collection_request_manager_method_prefix), return_value=10)
    @mock.patch('{}.get_routing_info'.format(collection_request_manager_method_prefix), return_value={})
    @mock.patch('{}.get_num_available_queue'.format(collection_request_manager_method_prefix), return_value=1)
    def test1_generate_collection_request(self, input1, input2, input3, input4, input5, input6, input7):
        helper.create_mock_dynamodb_collection_session_table()
        collection_request_manager.generate_collect_request()
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'human', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START', 'collectionName': 'name',
                             'routingInfo': {}}

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
    @mock.patch('{}.ask_collection_name'.format(collection_request_manager_method_prefix), return_value='name')
    @mock.patch('{}.ask_collection_mode'.format(collection_request_manager_method_prefix), return_value=False)
    @mock.patch('{}.ask_collection_goal'.format(collection_request_manager_method_prefix), return_value=10)
    @mock.patch('{}.ask_collection_bot'.format(collection_request_manager_method_prefix), return_value='OrderFlowers')
    def test2_generate_collection_request(self, input1, input2, input3, input4, input5, input6):
        helper.create_mock_dynamodb_collection_session_table()
        collection_request_manager.generate_collect_request()
        expected_response = {'collectionPIN': '123456', 'conversationPIN': '987654', 'mode': 'bot', 'contactIDs': [],
                             'collectionGoal': 10, 'collectionStatus': 'START',
                             'collectionBot': 'OrderFlowers', 'collectionName': 'name'}

        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456'})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_routing_info(self):
        helper.create_mock_dynamodb_queue_pool_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table('connectQueuePool')
        with table.batch_writer() as batch:
            routing_info = {'queueNumber': 1, 'queueID': 'test_queue_id',
                            'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info)
        # test 1
        expected_response = routing_info
        actual_response = collection_request_manager.get_routing_info()
        self.assertEqual(actual_response, expected_response)

        expected_response = 0
        actual_response = collection_request_manager.get_num_available_queue()
        self.assertEqual(actual_response, expected_response)

        # test 2
        with table.batch_writer() as batch:
            routing_info_num1 = {'queueNumber': 1, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num1)
            routing_info_num2 = {'queueNumber': 2, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num2)
            routing_info_num3 = {'queueNumber': 3, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num3)
        actual_response_num1 = collection_request_manager.get_routing_info()
        actual_response_num2 = collection_request_manager.get_routing_info()
        actual_response_num3 = collection_request_manager.get_routing_info()
        with table.batch_writer() as batch:
            batch.put_item(Item=actual_response_num1)
            batch.put_item(Item=actual_response_num2)
            batch.put_item(Item=actual_response_num3)

        expected_response = 3
        actual_response = collection_request_manager.get_num_available_queue()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_num_available_queue(self):
        helper.create_mock_dynamodb_queue_pool_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table('connectQueuePool')

        # test 1
        expected_response = 0
        actual_response = collection_request_manager.get_num_available_queue()
        self.assertEqual(actual_response, expected_response)

        # test 2
        with table.batch_writer() as batch:
            routing_info_num1 = {'queueNumber': 1, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num1)
            routing_info_num2 = {'queueNumber': 2, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num2)
            routing_info_num3 = {'queueNumber': 3, 'queueID': 'test_queue_id',
                                 'routingProfileID': 'test_routing_profile_id'}
            batch.put_item(Item=routing_info_num3)

        expected_response = 3
        actual_response = collection_request_manager.get_num_available_queue()
        self.assertEqual(actual_response, expected_response)

        # test 3
        table.delete_item(
            Key={
                'queueNumber': 1
            }
        )
        expected_response = 2
        actual_response = collection_request_manager.get_num_available_queue()
        self.assertEqual(actual_response, expected_response)


if __name__ == '__main__':
    unittest.main()
