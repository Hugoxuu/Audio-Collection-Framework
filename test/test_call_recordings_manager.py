# test_call_recordings_manager.py: Unit test for the framework

import unittest
import mock
import os
from aws_deep_sense_spoken_data_collection_framework.call_recordings_manager import CallRecordingsManager
import aws_deep_sense_spoken_data_collection_framework.utils as utils

# Retrieve AWS Access Key
test_data_directory = os.path.join(os.path.dirname(__file__), '..', 'test-data')
config_test_path = os.path.join(test_data_directory, 'aws_config_test')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_test_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_test_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_test_path)

# Create Class Objects
call_recordings_manager = CallRecordingsManager(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, CALL_RECORDINGS_BUCKET_NAME)


class TestCallRecordingsManage(unittest.TestCase):
    def test_parse_id_from_key(self):
        # test 1
        key = 'connect/user_name/sample_folder/sample-id_hour:minute_timezone.wav'
        id = call_recordings_manager.parse_contact_id_from_key(key)
        self.assertEqual(id, 'sample-id')

        # test 2
        key = 'folder/sample-id'
        expected_response = 'sample-id'
        actual_response = call_recordings_manager.parse_contact_id_from_key(key)
        self.assertEqual(actual_response, expected_response)

    @mock.patch('builtins.input', return_value='')
    def test_ask_output_directory(self, input):
        # test 1
        with mock.patch('builtins.input') as keyboard_mock:
            keyboard_mock.return_value = ''
            test_collection_pin = '123456'
            expected_response = os.path.join(os.getcwd(), 'audio_file', test_collection_pin)
            actual_response = call_recordings_manager.ask_output_directory(test_collection_pin)
            self.assertEqual(actual_response, expected_response)

        # test 2
        with mock.patch('builtins.input') as keyboard_mock:
            keyboard_mock.return_value = '/invalid_file_path/invalid_file_path/***'
            test_collection_pin = '123456'
            expected_response = os.path.join(os.getcwd(), 'audio_file', test_collection_pin)
            actual_response = call_recordings_manager.ask_output_directory(test_collection_pin)
            self.assertEqual(actual_response, expected_response)

        # test 3
        with mock.patch('builtins.input') as keyboard_mock:
            keyboard_mock.return_value = '/'
            test_collection_pin = '123456'
            expected_response = os.path.join(os.path.abspath('/'), test_collection_pin)
            actual_response = call_recordings_manager.ask_output_directory(test_collection_pin)
            self.assertEqual(actual_response, expected_response)


if __name__ == '__main__':
    unittest.main()
