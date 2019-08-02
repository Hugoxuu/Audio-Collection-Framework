# test_user_manager.py: Unit test for the framework

import unittest
import mock
import os
import boto3
from moto import mock_dynamodb2
from aws_deep_sense_spoken_data_collection_framework.user_manager import UserManager
import aws_deep_sense_spoken_data_collection_framework.utils as utils

# Set up default session for mocking AWS PYTHON SDK (boto3)
boto3.setup_default_session()

# Retrieve AWS Access Key
test_data_directory = os.path.join(os.path.dirname(__file__), '..', 'test-data')
config_test_path = os.path.join(test_data_directory, 'aws_config_test')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_test_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_test_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_test_path)
CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_ROUTING_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL = utils.get_connect_info(
    config_test_path)

# Create Class Objects
user_manager = UserManager(config_test_path, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                           CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_ROUTING_ID,
                           CONNECT_PHONE_NUMBER,
                           CONNECT_CCP_URL)
user_manager_method_prefix_list = ['aws_deep_sense_spoken_data_collection_framework', 'user_manager', 'UserManager']
user_manager_method_prefix = '.'.join(user_manager_method_prefix_list)


class TestUserManage(unittest.TestCase):
    user_manager.connect_create_user_account = mock.MagicMock(return_value={'UserId': 'test_id'})
    user_manager.auto_login_portal_given_pin = mock.MagicMock()

    @mock.patch('builtins.input', return_value='N')
    @mock.patch('{}.save2db'.format(user_manager_method_prefix))
    @mock.patch('{}.generate_user_pin'.format(user_manager_method_prefix),
                return_value='123456')
    def test_create_agent_user(self, input1, input2, input3):
        agent_name = 'Default Agent Name'
        expected_response = ('123456', {'username': 'agent_123456', 'password': 'Abcd123456', 'userId': 'test_id',
                                        'phoneNumber': 'test_phone_number', 'url': 'test_ccp_url'})
        actual_response = user_manager.create_agent_user(agent_name)
        self.assertEqual(actual_response, expected_response)

    @mock.patch('{}.save2db'.format(user_manager_method_prefix))
    @mock.patch('{}.generate_user_pin'.format(user_manager_method_prefix),
                return_value='123456')
    def test_get_user_account(self, input1, input2):
        expected_response = {'username': 'agent_123456', 'password': 'Abcd123456'}
        actual_response = user_manager.get_user_account('123456')
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_save2db(self):
        self.create_mock_dynamodb_user_account_table()
        name = 'test_name'
        user_pin = 'test_user_pin'
        role = 'test_role'
        account = {}
        user_manager.save2db(name, user_pin, role, account)
        expected_response = {utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: user_pin, 'name': name, 'type': role,
                             'account': account}

        table = user_manager.dynamodb.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: str(user_pin)})
        if 'Item' not in session:
            raise AssertionError
        actual_response = session['Item']
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_list_all_user(self):
        self.create_mock_dynamodb_user_account_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            name = 'test_name'
            user_pin = 'test_user_pin'
            role = 'test_role'
            account = {}
            user_item = {utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: user_pin, 'name': name, 'type': role,
                         'account': account}
            batch.put_item(Item=user_item)
        expected_response = [user_item]
        actual_response = user_manager.list_all_user()
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_check_user_type(self):
        self.create_mock_dynamodb_user_account_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: 'test_user_pin', 'type': 'test_role'}
            batch.put_item(Item=user_item)

        # test 1
        expected_response = 'test_role'
        actual_response = user_manager.check_user_type('test_user_pin')
        self.assertEqual(actual_response, expected_response)

        # test 2
        expected_response = ''
        actual_response = user_manager.check_user_type('invalid_user_pin')
        self.assertEqual(actual_response, expected_response)

    def test_get_phone_number(self):
        expected_response = user_manager.CONNECT_PHONE_NUMBER
        actual_response = user_manager.get_phone_number()
        self.assertEqual(actual_response, expected_response)

    def test_get_url(self):
        expected_response = user_manager.CONNECT_CCP_URL
        actual_response = user_manager.get_URL()
        self.assertEqual(actual_response, expected_response)

    def create_mock_dynamodb_user_account_table(self):
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


if __name__ == '__main__':
    unittest.main()
