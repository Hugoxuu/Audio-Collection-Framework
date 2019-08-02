import os
import time
import logging
import boto3
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import aws_deep_sense_spoken_data_collection_framework.utils as utils

CHROME_DRIVER_URL = 'https://chromedriver.storage.googleapis.com/75.0.3770.140/chromedriver_mac64.zip'
CHROME_DRIVER_NAME = 'chromedriver'


class UserManager:
    """
    This module manages the user account as conversation roles on Amazon Connect and
    relevant user information stored in AWS Dynamo DB

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param CONNECT_INSTANCE_ID: AWS Connect Instance ID
    :param CONNECT_SECURITY_ID: AWS Connect Default Security Profile ID for agent user
    :param CONNECT_ROUTING_ID: AWS Connect Default Routing Profile ID
    :param CONNECT_PHONE_NUMBER: AWS Connect Phone number for customer to call
    :param CONNECT_CCP_URL: AWS Connect Contact Center Portal (CCP) for agent user to login and receive the call
    """

    def __init__(self, config_path, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                 CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_ROUTING_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL):
        # Retrieve AWS Information
        self.ACCESS_KEY_ID = ACCESS_KEY_ID
        self.ACCESS_KEY = ACCESS_KEY
        self.AWS_REGION_NAME = AWS_REGION_NAME
        self.CONNECT_INSTANCE_ID = CONNECT_INSTANCE_ID
        self.CONNECT_SECURITY_ID = CONNECT_SECURITY_ID
        self.CONNECT_ROUTING_ID = CONNECT_ROUTING_ID
        self.CONNECT_PHONE_NUMBER = CONNECT_PHONE_NUMBER
        self.CONNECT_CCP_URL = CONNECT_CCP_URL
        self.config_path = config_path

        self.dynamodb = boto3.resource('dynamodb', region_name=self.AWS_REGION_NAME,
                                       aws_access_key_id=self.ACCESS_KEY_ID,
                                       aws_secret_access_key=self.ACCESS_KEY)

    def create_user(self):
        """
        Create a user as conversation role

        """
        decision = input('Select a conversation role (Press 1 for customer, 2 for agent): ')
        while decision != '1' and decision != '2':
            decision = input('Invalid input. Select a conversation role (Press 1 for customer, 2 for agent) : ')

        name = input('Please enter the name of the conversation role (blank for default name): ')
        if len(name) == 0:
            name = 'Default User Name'

        role = ''
        PIN = ''
        account = {}
        try:
            if decision == '1':
                role = 'customer'
                PIN, account = self.create_customer_user(name)
            elif decision == '2':
                role = 'agent'
                PIN, account = self.create_agent_user(name)
        except Exception as e:
            logging.error('Error: {}'.format(e))

        # Print out the information
        logging.info('Your user information is shown below:')
        logging.info('User Name: {}'.format(name))
        logging.info('User PIN: {}'.format(PIN))
        logging.info('Role: {}'.format(role))
        logging.info('Account Information: {}'.format(account))
        return

    def create_user_given_info(self, role, name):
        PIN = ''
        account = {}
        if role == 'customer':
            PIN, account = self.create_customer_user(name)
        elif role == 'agent':
            PIN, account = self.create_agent_user(name)
        else:
            logging.error('Error: Invalid role input.')

        return PIN, account

    def create_customer_user(self, name):
        """
        Create a customer user

        :return: 6-digit PIN and account information for the customer user that just created
        """
        PIN = self.generate_user_pin()
        role = 'customer'
        account = {}
        self.save2db(name, PIN, role, account)
        return PIN, account

    def create_agent_user(self, name):
        """
        Create an agent user

        :return: 6-digit PIN and  account information for the customer user that just created
        """
        PIN = self.generate_user_pin()
        role = 'agent'
        account = self.get_user_account(PIN)
        account['phoneNumber'] = self.get_phone_number()
        account['url'] = self.get_URL()

        response = self.connect_create_user_account(account['username'], account['password'], PIN)
        account['userId'] = response['UserId']

        self.save2db(name, PIN, role, account)
        return PIN, account

    def generate_user_pin(self):
        """
        Generate a unique 6-digit user PIN code for a customer or an agent

        :return: generated 6-digit user PIN code
        """
        num_digit = 6
        PIN = utils.random_with_n_digits(num_digit)
        while utils.is_user_pin_exists(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, PIN):
            PIN = utils.random_with_n_digits(num_digit)
        return PIN

    def save2db(self, name, PIN, role, account):
        """
        Save the user information into Dynamo DB

        :param PIN: 6-digit user PIN code
        :param role: user role type
        :param account: user account information
        """
        table = self.dynamodb.Table(utils.USER_ACCOUNT_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            user_item = {'name': name, 'PIN': PIN, 'type': role, 'account': account}
            batch.put_item(Item=user_item)
        return

    def list_all_user(self):
        """
        List all users and their basic information

        """
        # Get all requests from the table
        table = self.dynamodb.Table('userAccount')
        user_list = table.scan()['Items']
        for user in user_list:
            name = user['name']
            PIN = user['PIN']
            role = user['type']
            account = user['account']
            logging.info('User Name: {}, PIN: {}, role: {}, account: {}'.format(name, PIN, role, account))
        logging.info('All users are listed.')
        return user_list

    def connect_create_user_account(self, username, password, PIN):
        """
        Call the Amazon Connect API to create a new user account

        :param username: as named
        :param password: as named
        :param PIN: 6-digit user PIN code
        :return: user account information sent from Amazon Connect, containing user account id
        """
        connect = boto3.client('connect', region_name=self.AWS_REGION_NAME, aws_access_key_id=self.ACCESS_KEY_ID,
                               aws_secret_access_key=self.ACCESS_KEY)
        # Send request to Amazon Connect
        response = connect.create_user(
            Username=username,
            Password=password,
            IdentityInfo={
                'FirstName': 'agent',
                'LastName': PIN,
                'Email': ''
            },
            PhoneConfig={
                'PhoneType': 'SOFT_PHONE',
                'AutoAccept': False,
                'AfterContactWorkTimeLimit': 0,
                'DeskPhoneNumber': ''
            },
            SecurityProfileIds=[
                self.CONNECT_SECURITY_ID,
            ],
            RoutingProfileId=self.CONNECT_ROUTING_ID,
            InstanceId=self.CONNECT_INSTANCE_ID
        )
        return response

    def cache_chrome_driver(self):
        """
        Cache the chrome driver for auto login

        :return: The path of chrome driver
        """
        config_directory = self.config_path.rsplit('/', 1)[0]
        driver_local_path = os.path.join(config_directory, CHROME_DRIVER_NAME)
        try:
            if not os.path.exists(driver_local_path):
                driver_local_path_zip = os.path.join(config_directory, CHROME_DRIVER_URL.rsplit('/', 1)[-1])
                urllib.request.urlretrieve(CHROME_DRIVER_URL, driver_local_path_zip)
                with utils.ZipFileWithPermission(driver_local_path_zip, 'r') as zip_object:
                    for zip_file_info in zip_object.infolist():
                        zip_object.extract(zip_file_info, path=config_directory)
                os.remove(driver_local_path_zip)
        except Exception as e:
            logging.error('Error: {}'.format(e))
        return driver_local_path

    def auto_login_portal(self):
        """
        Ask for the agent PIN and Login to the Amazon Connect portal

        """
        # Ask the user for a valid PIN code
        PIN = utils.ask_user_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        if self.check_user_type(PIN) != 'agent':
            logging.error('Error: Must be an agent account')
            return

        self.auto_login_portal_given_pin(PIN)
        return

    def auto_login_portal_given_pin(self, agent_pin):
        url = self.get_URL()
        user_account = self.get_user_account(agent_pin)
        driver_local_path = self.cache_chrome_driver()
        """
        Auto login the Amazon Connect page with given agent user account

        :param url: Amazon Connect URL
        :param user_account: user account information
        """
        # Default setting for the CCP popup window
        WINDOW_SIZE = "320,465"
        chrome_options = Options()
        chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        chrome_options.add_argument("--app=%s" % url)
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--incognito")
        chrome_options.add_experimental_option("detach", True)

        # Default HTML id for input
        username_id = 'wdc_username'
        password_id = 'wdc_password'
        sign_in_button_id = 'wdc_login_button'
        username_str = user_account['username']
        password_str = user_account['password']

        # Start auto login
        try:
            browser = webdriver.Chrome(executable_path=driver_local_path, chrome_options=chrome_options)
            try:
                browser.get(url)
                # Only wait the page to be loaded for certain time (seconds), to prevent infinite waiting
                wait_time = 15
                check_interval = 0.5  # The time interval (seconds) of checking if the page is loaded
                for i in range(int(wait_time / check_interval)):
                    try:
                        username = browser.find_element_by_id(username_id)
                        username.send_keys(username_str)
                        password = browser.find_element_by_id(password_id)
                        password.send_keys(password_str)
                        signin_button = browser.find_element_by_id(sign_in_button_id)
                        signin_button.click()
                        break
                    except:  # Exception happens when the page is not fully loaded
                        time.sleep(check_interval)
            except Exception as e:  # Exception happens when the url is not valid
                logging.error('Error: {}'.format(e))
                browser.close()
        except Exception as e:
            logging.error('Error: {}'.format(e))
        return

    def check_user_type(self, PIN):
        """
        Check the user role type given the user PIN
        :param PIN: 6-digit user PIN code
        :return: user role type
        """
        table = self.dynamodb.Table('userAccount')
        session = table.get_item(Key={utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: str(PIN)})
        if 'Item' in session:
            return session['Item']['type']
        return ''

    def delete_user(self):
        """
        Ask user for a PIN and Delete a user associated with this PIN

        """
        PIN = utils.ask_user_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        # Ask the user to confirm
        decision = input(
            'Are you sure to delete this user? Y/N | ')
        if decision != 'Y' and decision != 'y':
            return

        self.delete_user_given_pin(PIN)
        logging.info('User {} is deleted.'.format(PIN))
        return

    def delete_all_user(self):
        """
        Delete all users

        """
        # Ask the user to confirm
        decision = input(
            'Are you sure to delete all users? Y/N | ')
        if decision != 'Y' and decision != 'y':
            return
        # Get all sessions from the table
        table = self.dynamodb.Table('userAccount')
        session_list = table.scan()['Items']
        for item in session_list:
            PIN = item[utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY]
            self.delete_user_given_pin(PIN)
            logging.info('User {} is deleted.'.format(PIN))

        logging.info('All users are deleted.')
        return

    def delete_user_given_pin(self, PIN):
        """
        Delete a certain user given a valid PIN

        :param PIN: 6-digit user PIN code
        """
        table = self.dynamodb.Table('userAccount')
        session = table.get_item(Key={utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: str(PIN)})
        error_list = []
        if 'Item' in session:
            role = session['Item']['type']
            # Delete this item from the table
            try:
                table.delete_item(Key={utils.USER_ACCOUNT_DYNAMODB_TABLE_KEY: PIN})
            except:
                error_message = 'Error: Failed to delete user information on AWS DynamoDB'
                logging.error(error_message)
                error_list.append(error_message)
            # Delete user account on Amazon Connect
            if role == 'agent':
                try:
                    user_id = session['Item']['account']['userId']
                    connect = boto3.client('connect', region_name=self.AWS_REGION_NAME,
                                           aws_access_key_id=self.ACCESS_KEY_ID,
                                           aws_secret_access_key=self.ACCESS_KEY)
                    connect.delete_user(
                        InstanceId=self.CONNECT_INSTANCE_ID,
                        UserId=user_id
                    )
                except:
                    error_message = 'Error: Failed to delete user account on Amazon Connect'
                    logging.error(error_message)
                    error_list.append(error_message)
        else:
            error_list.append('Error: Invalid user PIN.')
        return error_list

    def get_phone_number(self):
        """
        Get the phone number for the user to call

        :return: valid phone number
        """
        return self.CONNECT_PHONE_NUMBER

    def get_URL(self):
        """
        Get the URL of the Amazon Connect web portal

        :return: valid Amazon Connect URL
        """
        return self.CONNECT_CCP_URL

    @staticmethod
    def get_user_account(PIN):
        """
        Retrieve the account information

        :param PIN: 6-digit user PIN code
        :return: user account information
        """
        username = 'agent_' + PIN  # Default
        password = 'Abcd' + PIN  # Default
        return {'username': username, 'password': password}
