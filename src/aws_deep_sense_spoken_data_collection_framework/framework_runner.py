# framework_runner.py:  Please use the framework by running this module.
#                       This program takes several command line arguments as input and will
#                       execute different operations by calling functions in other modules.

import argparse
import os
import sys
import logging

# Set the logging level so that INFO log can show in the terminal
logging.getLogger().setLevel(logging.INFO)

# Add module directory into system path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import aws_deep_sense_spoken_data_collection_framework.utils as utils
from aws_deep_sense_spoken_data_collection_framework.call_recordings_manager import CallRecordingsManager
from aws_deep_sense_spoken_data_collection_framework.collection_request_manager import CollectionRequestManager
from aws_deep_sense_spoken_data_collection_framework.user_manager import UserManager

# Change to your desired configuration file
config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configurations', 'aws_config')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_path)
CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL = utils.get_connect_info(config_path)


def parser_add_argument():
    """
    Add the possible argument into command line

    """
    parser = argparse.ArgumentParser(description='Framework for Spoken and IVR Data Collection')
    parser.add_argument('-sc', '--startCollection', action='store_true',
                        help='start a new collection request')
    parser.add_argument('-gc', '--getCollection', action='store_true',
                        help='get the information of an ongoing collection request')
    parser.add_argument('-cs', '--changeCollectionStatus', action='store_true',
                        help='change the collection status of an onging collection request')
    parser.add_argument('-lc', '--listCollection', action='store_true',
                        help='list all ongoing collection requests')
    parser.add_argument('-cu', '--createUser', action='store_true',
                        help='create a new user as conversation role')
    parser.add_argument('-lu', '--listAllUser', action='store_true',
                        help='list all users')
    parser.add_argument('-op', '--openConnectPortal', action='store_true',
                        help='open the browser window for Amazon Connect Contact portal')
    parser.add_argument('-du', '--deleteUser', action='store_true',
                        help='delete a user')
    parser.add_argument('-da', '--deleteAllUser', action='store_true',
                        help='delete all users')
    parser.add_argument('-dc', '--download', action='store_true',
                        help='download call recordings and corresponding metadata from AWS S3')
    parser.add_argument('-gt', '--getTranscribe', action='store_true',
                        help='apply machine transcribe to call recordings for fast benchmarking purpose')
    args = parser.parse_args()
    return args


def main():
    """
    Perform action based on command-line arguments, **only one operation is supported at a time**
    There are 3 categories of operations:
    1. Collection Request Manager operations
    2. User Manager operations
    3. Call Recordings Manager operations

    """
    args = parser_add_argument()
    if args.startCollection or args.getCollection or args.changeCollectionStatus or args.listCollection:
        collection_request_manager = CollectionRequestManager(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                                              CALL_RECORDINGS_BUCKET_NAME)
        if args.startCollection:
            print('Start a new collection request...')
            return collection_request_manager.generate_collect_request()
        elif args.getCollection:
            print('Retrieve the information of a collection request...')
            return collection_request_manager.get_collection_request()
        elif args.changeCollectionStatus:
            print('Change the collection status of an onging collection request...')
            return collection_request_manager.change_collection_status()
        elif args.listCollection:
            print('List all ongoing collection requests...')
            return collection_request_manager.list_collect_requests()

    elif args.createUser or args.listAllUser or args.openConnectPortal or args.deleteUser or args.deleteAllUser:
        user_manager = UserManager(config_path, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                   CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL)
        if args.createUser:
            print('Create a new user as conversation role...')
            return user_manager.create_user()
        elif args.listAllUser:
            print('List all users...')
            return user_manager.list_all_user()
        elif args.openConnectPortal:
            print('Login to the Amazon Connect Portal...')
            return user_manager.auto_login_portal()
        elif args.deleteUser:
            print('Delete a user...')
            return user_manager.delete_user()
        elif args.deleteAllUser:
            print('Delete all users...')
            return user_manager.delete_all_user()

    elif args.download or args.getTranscribe:
        call_recordings_manager = CallRecordingsManager(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                                        CALL_RECORDINGS_BUCKET_NAME)
        if args.download:
            print('Start downloading call recordings from AWS S3...')
            return call_recordings_manager.download_call_recordings()
        elif args.getTranscribe:
            print('Get text transcribe of previous call recordings...')
            return call_recordings_manager.get_transcribe()


if __name__ == "__main__":
    main()
