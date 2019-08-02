# test_utils.py: Unit test for the framework

import unittest
import mock
from moto import mock_dynamodb2
import os
import logging
import zipfile
import boto3
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


class TestUtils(unittest.TestCase):
    def test_random_with_n_digits(self):
        num_PIN = 99  # Test range: 2 - 100
        # Generate PIN codes
        for i in range(num_PIN):
            num_digits = i + 1
            PIN = utils.random_with_n_digits(num_digits)
            # Make sure every PIN has the expected length
            expected_response = num_digits
            actual_response = len(PIN)
            self.assertEqual(actual_response, expected_response)

    def test_parse_config(self):
        expected_response = {'AWS_ACCESS_KEY_ID': 'AAAAAAAAAAAAAAAAAAAA',
                             'AWS_ACCESS_KEY': 'BBBBB/BBBBBBBBB+BBBBBBB+BBBBB/BBBBBBBBBB',
                             'AWS_REGION_NAME': 'us-east-1',
                             'CALL_RECORDINGS_BUCKET_NAME': 'callrecordings_bucket',
                             'CONNECT_INSTANCE_ID': 'test_connect_instance_id',
                             'CONNECT_SECURITY_ID': 'test_connect_security_id',
                             'CONNECT_ROUTING_ID': 'test_connect_routing_id',
                             'CONNECT_PHONE_NUMBER': 'test_phone_number',
                             'CONNECT_CCP_URL': 'test_ccp_url'
                             }
        actual_response = utils.parse_config(config_test_path)
        self.assertEqual(actual_response, expected_response)

    def test_get_aws_access_key(self):
        expected_response = ('AAAAAAAAAAAAAAAAAAAA', 'BBBBB/BBBBBBBBB+BBBBBBB+BBBBB/BBBBBBBBBB')
        actual_response = utils.get_aws_access_key(config_test_path)
        self.assertEqual(actual_response, expected_response)

    def test_get_aws_region_name(self):
        expected_response = 'us-east-1'
        actual_response = utils.get_aws_region_name(config_test_path)
        self.assertEqual(actual_response, expected_response)

    def test_get_call_recordings_bucket_name(self):
        expected_response = 'callrecordings_bucket'
        actual_response = utils.get_call_recordings_bucket_name(config_test_path)
        self.assertEqual(actual_response, expected_response)

    def test_get_connect_info(self):
        expected_response = (
            'test_connect_instance_id', 'test_connect_security_id', 'test_connect_routing_id', 'test_phone_number',
            'test_ccp_url')
        actual_response = utils.get_connect_info(config_test_path)
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_is_collection_pin_exists(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '12345'}
            batch.put_item(Item=user_item)

        # Test 1
        expected_response = True
        actual_response = utils.is_collection_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '12345')
        self.assertEqual(actual_response, expected_response)

        # Test 2
        expected_response = False
        actual_response = utils.is_collection_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '98765')
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_is_conversation_pin_exists(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '12345',
                         utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: '98765'}
            batch.put_item(Item=user_item)

        # Test 1
        expected_response = True
        actual_response = utils.is_conversation_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '98765')
        self.assertEqual(actual_response, expected_response)

        # Test 2
        expected_response = False
        actual_response = utils.is_conversation_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '12345')
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_is_user_pin_exists(self):
        self.create_mock_dynamodb_user_account_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: '123456'}
            batch.put_item(Item=user_item)

        # Test 1
        expected_response = True
        actual_response = utils.is_user_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '123456')
        self.assertEqual(actual_response, expected_response)

        # Test 2
        expected_response = False
        actual_response = utils.is_user_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '987654')
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('builtins.input', return_value='12345')
    def test_ask_collection_pin(self, input):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '12345'}
            batch.put_item(Item=user_item)

        expected_response = '12345'
        actual_response = utils.ask_collection_pin(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME)
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    @mock.patch('builtins.input', return_value='123456')
    def test_ask_user_pin(self, input):
        self.create_mock_dynamodb_user_account_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: '123456'}
            batch.put_item(Item=user_item)

        expected_response = '123456'
        actual_response = utils.ask_user_pin(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME)
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_get_contact_ids(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        contact_id_list = ['1', '2', '3']
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456', 'contactIDs': contact_id_list}
            batch.put_item(Item=user_item)

        # test 1
        expected_response = contact_id_list
        actual_response = utils.get_contact_ids(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '123456')
        self.assertEqual(actual_response, expected_response)

        # test 2
        expected_response = []
        actual_response = utils.get_contact_ids(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, 'invalid_collection_pin')
        self.assertEqual(actual_response, expected_response)

    @mock_dynamodb2
    def test_check_collection_request_mode(self):
        self.create_mock_dynamodb_collection_session_table()
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
        table = dynamodb_resource.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        mode = 'human'
        with table.batch_writer() as batch:
            user_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: '123456', 'mode': mode}
            batch.put_item(Item=user_item)

        # test 1
        expected_response = mode
        actual_response = utils.check_collection_request_mode(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, '123456')
        self.assertEqual(actual_response, expected_response)

        # test 2
        expected_response = 'none'
        actual_response = utils.check_collection_request_mode(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                                              'invalid_collection_pin')
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

    def test_ZipFileWithPermission(self):
        sample_executable_zip_path = os.path.join(test_data_directory, 'sample_executable.zip')
        with zipfile.ZipFile(sample_executable_zip_path, 'r') as zip_object:
            for zip_file_info in zip_object.infolist():
                zip_object.extract(zip_file_info, path=test_data_directory)
        sample_executable_path = os.path.join(test_data_directory, 'sample_executable')
        st = os.stat(sample_executable_path)

        # Normal unzip will break the permission into 33188
        if st.st_mode != 33188:
            logging.error('Error: sample_executable.zip is broken')
            os.remove(sample_executable_path)

        # 'utils.ZipFileWithPermission' shall keep the file permission, which is 33216
        with utils.ZipFileWithPermission(sample_executable_zip_path, 'r') as zip_object:
            for zip_file_info in zip_object.infolist():
                zip_object.extract(zip_file_info, path=test_data_directory)
        sample_executable_path = os.path.join(test_data_directory, 'sample_executable')
        st = os.stat(sample_executable_path)
        expected_response = 33216
        actual_response = st.st_mode
        self.assertEqual(actual_response, expected_response)
        os.remove(sample_executable_path)


if __name__ == '__main__':
    unittest.main()
