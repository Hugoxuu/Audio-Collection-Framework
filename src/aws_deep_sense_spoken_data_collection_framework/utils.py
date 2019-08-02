# utils.py: Provides utility methods that will be used among other modules


import boto3
from boto3.dynamodb.conditions import Key
import os
from random import randint
from zipfile import ZipFile, ZipInfo


ACCESS_KEY_ID__CONFIG_KEY = 'AWS_ACCESS_KEY_ID'
ACCESS_KEY__CONFIG_KEY = 'AWS_ACCESS_KEY'
AWS_REGION_NAME__CONFIG_KEY = 'AWS_REGION_NAME'
CALL_RECORDINGS_BUCKET_NAME__CONFIG_KEY = 'CALL_RECORDINGS_BUCKET_NAME'
CONNECT_INSTANCE_ID__CONFIG_KEY = 'CONNECT_INSTANCE_ID'
CONNECT_SECURITY_ID__CONFIG_KEY = 'CONNECT_SECURITY_ID'
CONNECT_ROUTING_ID__CONFIG_KEY = 'CONNECT_ROUTING_ID'
CONNECT_PHONE_NUMBER__CONFIG_KEY = 'CONNECT_PHONE_NUMBER'
CONNECT_CCP_URL__CONFIG_KEY = 'CONNECT_CCP_URL'

COLLECTION_REQUEST_DYNAMODB_TABLE = 'collectionSession'
COLLECTION_REQUEST_DYNAMODB_TABLE_KEY = 'collectionPIN'
COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX = 'conversationPIN-index'
COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY = 'conversationPIN'
USER_ACCOUNT_DYNAMODB_TABLE = 'userAccount'
USER_ACCOUNT_DYNAMODB_TABLE_KEY = 'PIN'

def parse_config(config_file):
    """
    Parse the aws_config file into dictionary

    :param config_file: path for configuration file
    :return: information dict in the configuration file
    """
    config_dict = {}
    with open(config_file, 'r') as config:
        for line in config:
            key, val = line.split()
            config_dict[key] = val
    return config_dict


def get_aws_access_key(config_file):
    """
    Parse the AWS Access Key from aws_config file

    :param config_file: path for configuration file
    :return: Access credentials for AWS account
    """
    config_dict = parse_config(config_file)
    ACCESS_KEY_ID = config_dict[ACCESS_KEY_ID__CONFIG_KEY]
    ACCESS_KEY = config_dict[ACCESS_KEY__CONFIG_KEY]
    return ACCESS_KEY_ID, ACCESS_KEY


def get_call_recordings_bucket_name(config_file):
    """
    Parse the AWS S3 Bucket Name from aws_config file

    :param config_file: path for configuration file
    :return: AWS S3 bucket names for storing the call recordings
    """
    config_dict = parse_config(config_file)
    CALL_RECORDINGS_BUCKET_NAME = config_dict[CALL_RECORDINGS_BUCKET_NAME__CONFIG_KEY]

    return CALL_RECORDINGS_BUCKET_NAME


def get_connect_info(config_file):
    """
    Parse the Amazon Connect Instance ID from aws_config file

    :param config_file: path for configuration file
    :return: AWS Connect parameters
    """
    config_dict = parse_config(config_file)
    CONNECT_INSTANCE_ID = config_dict[CONNECT_INSTANCE_ID__CONFIG_KEY]
    CONNECT_SECURITY_ID = config_dict[CONNECT_SECURITY_ID__CONFIG_KEY]
    CONNECT_ROUTING_ID = config_dict[CONNECT_ROUTING_ID__CONFIG_KEY]
    CONNECT_PHONE_NUMBER = config_dict[CONNECT_PHONE_NUMBER__CONFIG_KEY]
    CONNECT_CCP_URL = config_dict[CONNECT_CCP_URL__CONFIG_KEY]
    return CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_ROUTING_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL


def get_aws_region_name(config_file):
    """
    Parse the AWS Region name from aws_config file

    :param config_file: path for configuration file
    :return: AWS Region name
    """
    config_dict = parse_config(config_file)
    AWS_REGION_NAME = config_dict[AWS_REGION_NAME__CONFIG_KEY]
    return AWS_REGION_NAME


def random_with_n_digits(n):
    """
    Generate a digit code randomly
    Requires: n >= 1

    :param n: number of digits for the code
    :return: n-digit code
    """
    num_digit = n
    start = 10 ** (num_digit - 1)
    end = 10 ** num_digit - 1
    return str(randint(start, end))


def ask_collection_pin(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME):
    """
    Ask the user for a valid collection PIN code by checking AWS Dynamo DB

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :return: valid user-input collection PIN code
    """
    # Ask the user for a valid PIN code
    PIN = input('Enter your collection PIN code: ')
    while len(PIN) == 0 or not is_collection_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, PIN):
        PIN = input('Invalid PIN code. Enter PIN code again: ')
    return PIN


def ask_user_pin(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME):
    """
    Ask the user for a valid user PIN code by checking AWS Dynamo DB

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :return: valid user-input user PIN code
    """
    # Ask the user for a valid PIN code
    PIN = input('Enter your user PIN code: ')
    while len(PIN) == 0 or not is_user_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, PIN):
        PIN = input('Invalid PIN code. Enter PIN code again: ')
    return PIN


def is_collection_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, PIN):
    """
    Check if a collection PIN code exists

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param PIN: user-input collection PIN code
    :return: boolean indicating if the user-input collection PIN code exists
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    table = dynamodb.Table(COLLECTION_REQUEST_DYNAMODB_TABLE)
    session = table.get_item(Key={COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(PIN)})
    is_exists = 'Item' in session
    return is_exists


def is_conversation_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, PIN):
    """
    Check if a conversation PIN code exists

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param PIN: user-input conversation PIN code
    :return: boolean indicating if the user-input conversation PIN code exists
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    table = dynamodb.Table(COLLECTION_REQUEST_DYNAMODB_TABLE)
    resp = table.query(
        # Add the name of the index you want to use in your query.
        IndexName=COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX,
        KeyConditionExpression=Key(COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY).eq(PIN),
    )
    is_exists = resp['Count'] > 0
    return is_exists


def is_user_pin_exists(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, PIN):
    """
    Check if a user PIN code exists

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param PIN: user-input user PIN code
    :return: boolean indicating if the user-input user PIN code exists
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    table = dynamodb.Table(USER_ACCOUNT_DYNAMODB_TABLE)
    session = table.get_item(Key={USER_ACCOUNT_DYNAMODB_TABLE_KEY: str(PIN)})
    is_exists = 'Item' in session
    return is_exists


def get_contact_ids(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, collection_pin):
    """
    Get all contact ids from given PIN code

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param collection_pin: user-input collection PIN code
    :return: All contact ids associated with this collection request
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    table = dynamodb.Table(COLLECTION_REQUEST_DYNAMODB_TABLE)
    session = table.get_item(Key={COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})
    list_ids = []
    if 'Item' in session:
        list_ids = session['Item']['contactIDs']
    return list_ids


def check_collection_request_mode(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, collection_pin):
    """
    Check the mode of a collection request

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param collection_pin: user-input collection PIN code
    :return: Human/Human collection mode (return 'human') | Human/Bot collection mode (return 'bot') | (return 'none')
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    table = dynamodb.Table(COLLECTION_REQUEST_DYNAMODB_TABLE)
    session = table.get_item(Key={COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})
    mode = 'none'
    if 'Item' in session:
        mode = session['Item']['mode']
    return mode


# Subclassing ZipFile and Changing extract() Use to unzip file without corrupting the file permission
class ZipFileWithPermission(ZipFile):
    def extract(self, member, path=None, pwd=None):
        """
        Unzip file without corrupting the file permission
        :param member: zip file to unzip
        :param path: file path
        :param pwd: present working directory
        :return: unzipped files
        """
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        if attr:
            os.chmod(ret_val, attr)

        return ret_val
