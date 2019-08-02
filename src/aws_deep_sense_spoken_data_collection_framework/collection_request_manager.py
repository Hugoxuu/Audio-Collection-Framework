import logging
import boto3
import aws_deep_sense_spoken_data_collection_framework.utils as utils
from aws_deep_sense_spoken_data_collection_framework.call_recordings_manager import CallRecordingsManager


class CollectionRequestManager:
    """
    This module manages the conversation requests on Amazon Connect and
    relevant conversation information stored in AWS Dynamo DB

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param CALL_RECORDINGS_BUCKET_NAME: AWS S3 bucket name for storing the call recordings
    """

    def __init__(self, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, CALL_RECORDINGS_BUCKET_NAME):
        # Retrieve AWS Information
        self.ACCESS_KEY_ID = ACCESS_KEY_ID
        self.ACCESS_KEY = ACCESS_KEY
        self.AWS_REGION_NAME = AWS_REGION_NAME

        self.call_recordings_manage = CallRecordingsManager(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME,
                                                            CALL_RECORDINGS_BUCKET_NAME)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.AWS_REGION_NAME,
                                       aws_access_key_id=self.ACCESS_KEY_ID,
                                       aws_secret_access_key=self.ACCESS_KEY)

    def generate_collect_request(self):
        """
        Generate a new collection request

        """
        try:
            collection_pin = self.generate_collection_pin()
            conversation_pin = self.generate_conversation_pin()
            is_human_to_human = self.ask_collection_mode()
            collection_goal = self.ask_collection_goal()
            collection_status = 'START'
            if is_human_to_human:
                mode = 'human'
                category_info = self.ask_collection_category()
                self.save2db(collection_pin, conversation_pin, mode, category_info, collection_goal, collection_status)
                self.collection_request_printer(collection_pin, conversation_pin, mode,
                                                category_info['collectionCategory'], collection_goal, collection_status)
            else:
                mode = 'bot'
                bot_info = self.ask_collection_bot()
                self.save2db(collection_pin, conversation_pin, mode, bot_info, collection_goal, collection_status)
                self.collection_request_printer(collection_pin, conversation_pin, mode, bot_info['collectionBot'],
                                                collection_goal, collection_status)
        except Exception as e:
            logging.error('Error: {}'.format(e))
        return

    def generate_collection_request_given_info(self, mode, collection_category, collection_goal):
        collection_pin = self.generate_collection_pin()
        conversation_pin = self.generate_conversation_pin()
        collection_status = 'START'
        if mode == 'human':
            table = self.dynamodb.Table('collectionCategory')
            session = table.get_item(Key={"category": str(collection_category)})
            queue_arn = session['Item']['queueArn']
            category_info = {'collectionCategory': collection_category, 'queueArn': queue_arn}
            self.save2db(collection_pin, conversation_pin, mode, category_info, collection_goal, collection_status)
        elif mode == 'bot':
            bot_info = {'collectionBot': collection_category}
            self.save2db(collection_pin, conversation_pin, mode, bot_info, collection_goal, collection_status)
        return collection_pin, conversation_pin

    def generate_collection_pin(self):
        """
        Generate a unique collection PIN code as collection request PIN

        :return: generated 5-digit PIN collection request PIN code
        """
        num_digit = 5
        PIN = utils.random_with_n_digits(num_digit)
        while utils.is_collection_pin_exists(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, PIN):
            PIN = utils.random_with_n_digits(num_digit)
        return PIN

    def generate_conversation_pin(self):
        """
        Generate a unique 5-digit PIN code as conversation PIN

        :return: generated 5-digit PIN conversation PIN code
        """
        num_digit = 5
        PIN = utils.random_with_n_digits(num_digit)
        while utils.is_conversation_pin_exists(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, PIN):
            PIN = utils.random_with_n_digits(num_digit)
        return PIN

    def ask_collection_mode(self):
        """
        Ask the user for the desired collection mode

        :return: if the user-selected collection mode is human/human
        """
        print('Please choose among the following collection modes:')
        print('Human/Human - Enter 1')
        print('Human/Bot - Enter 2')
        mode_num = 2
        choice = input('Your choice: ')
        while not self.is_number_choice_valid(choice, mode_num):
            choice = input('Invalid input. Your choice: ')
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            raise ValueError  # Should not reach here normally

    def ask_collection_category(self):
        """
        Ask the user for the desired collection category

        :return: the user-selected collection category, along with the corresponding queue ARN
        """
        table = self.dynamodb.Table('collectionCategory')
        session_list = table.scan()['Items']
        print('Please choose among the following categories:')
        for index, item in enumerate(session_list, start=1):
            print('{} - Enter {}'.format(item['category'], index))
        choice = input('Your choice: ')
        while not self.is_number_choice_valid(choice, len(session_list)):
            choice = input('Invalid input. Your choice: ')
        choice_index = int(choice) - 1
        collection_category = session_list[choice_index]['category']
        queue_arn = session_list[choice_index]['queueArn']
        return {'collectionCategory': collection_category, 'queueArn': queue_arn}

    def ask_collection_bot(self):
        """
        Ask the user for the desired collection bot

        :return: the user-selected collection bot
        """
        table = self.dynamodb.Table('collectionBot')
        session_list = table.scan()['Items']
        print('Please choose among the following bots:')
        for index, item in enumerate(session_list, start=1):
            print('{} - Enter {}'.format(item['bot'], index))
        choice = input('Your choice: ')
        while not self.is_number_choice_valid(choice, len(session_list)):
            choice = input('Invalid input. Your choice: ')
        choice_index = int(choice) - 1
        collection_bot = session_list[choice_index]['bot']
        return {'collectionBot': collection_bot}

    def get_available_collection_category(self):
        try:
            category_table = self.dynamodb.Table('collectionCategory')
            category_list = category_table.scan()['Items']
            bot_table = self.dynamodb.Table('collectionBot')
            bot_list = bot_table.scan()['Items']
            return category_list, bot_list
        except Exception as e:
            logging.error('Cannot get available collection category information from DynamoDB, error: {}'.format(e))
            return [], []

    def save2db(self, collection_pin, conversation_pin, mode, collection_choice, collection_goal, collection_status):
        """
        Save the collection request information into Dynamo DB

        :param collection_pin: collection request PIN
        :param conversation_pin: conversation PIN
        :param collection_choice: collection request category
        :param mode: collection request mode
        :param collection_goal: number of conversations to be collected in this collection request
        :param collection_status: START | PAUSE | STOP

        """
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            collection_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin,
                               utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: conversation_pin, 'mode': mode,
                               'contactIDs': [], 'collectionGoal': collection_goal,
                               'collectionStatus': collection_status}
            collection_item.update(collection_choice)
            batch.put_item(Item=collection_item)
        return

    def get_collection_request(self):
        """
        Retrieve the information of an ongoing collection request

        """
        collection_pin = utils.ask_collection_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        response = self.get_collection_request_given_pin(collection_pin)
        if 'error' not in response:
            self.collection_request_printer(response['collection_pin'], response['conversation_pin'], response['mode'],
                                            response['collection_info'], response['collection_goal'],
                                            response['collection_status'])
        else:
            logging.error(response['error'])
        return

    def get_collection_request_given_pin(self, collection_pin):
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})

        # Get parameters from session item
        if 'Item' in session:
            conversation_pin = session['Item']['conversationPIN']
            mode = session['Item']['mode']
            collection_info = ''
            if mode == 'human':
                collection_info = session['Item']['collectionCategory']
            elif mode == 'bot':
                collection_info = session['Item']['collectionBot']
            contact_ids = session['Item']['contactIDs']
            collection_goal = session['Item']['collectionGoal']
            collection_status = session['Item']['collectionStatus']

            response = {'collection_pin': collection_pin, 'conversation_pin': conversation_pin, 'mode': mode,
                        'collection_info': collection_info, 'contact_ids': contact_ids,
                        'collection_goal': collection_goal, 'collectionStatus': collection_status}
        else:
            response = {'error': 'Error: Invalid Collection PIN or No session information was found.'}
        return response

    def list_collect_requests(self):
        """
        List all ongoing collection requests

        """
        # Get all requests from the table
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        collection_request_list = table.scan()['Items']
        for item in collection_request_list:
            collection_pin = item[utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY]
            contact_ids = item['contactIDs']
            conversation_pin = item['conversationPIN']
            mode = item['mode']
            collection_goal = item['collectionGoal']
            collection_status = item['collectionStatus']
            collection_info = ''
            if mode == 'human':
                collection_info = item['collectionCategory']
            elif mode == 'bot':
                collection_info = item['collectionBot']

            logging.info(
                'Collection PIN: {}, conversation PIN: {}, mode: {}, category: {}, collection progress: {}/{}, collection status: {}.'.format(
                    collection_pin, conversation_pin, mode, collection_info, len(contact_ids), collection_goal,
                    collection_status))
        logging.info('All sessions are listed.')
        return collection_request_list

    def end_collect_request(self):
        """
        End a collection session by deleting all related information on Amazon Connect, AWS Dynamo DB, and AWS S3

        """
        collection_pin = utils.ask_collection_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        # Ask the user to confirm
        decision = input(
            'Are you sure to end this conversation session? Y/N | ')
        if decision != 'Y' and decision != 'y':
            return

        self.end_request_given_pin(collection_pin)
        return

    def end_request_given_pin(self, collection_pin):
        """
        End the collection request given a PIN code

        :param collection_pin: collection request PIN
        """
        # Get user id info in AWS Dynamo DB
        collection_request_table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        try:
            # Delete call recordings in AWS S3
            self.call_recordings_manage.delete_call_recordings_given_pin(collection_pin)
        except:
            logging.error('Error: Cannot delete call recordings in S3')
        try:
            # Delete request information in AWS Dynamo DB
            collection_request_table.delete_item(Key={"collectionPIN": collection_pin})
        except:
            logging.error('Error: Cannot delete collect request information in AWS Dynamo DB')
        logging.info('Collect request {} is ended.'.format(collection_pin))
        return

    def end_all_collect_requests(self):
        """
        End all conversation requests in the AWS account

        """
        # Ask the user to confirm
        decision = input(
            'Are you sure to end all your collect requests? Y/N | ')
        if decision != 'Y' and decision != 'y':
            return
        # Get all requests from the table
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session_list = table.scan()['Items']
        for item in session_list:
            PIN = item[utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY]
            self.end_request_given_pin(PIN)

        logging.info('All collect requests are ended.')
        return

    def change_collection_status(self):
        """
        Change current collection status to desired collection status
        """
        collection_pin = utils.ask_collection_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        current_collection_status = \
            self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE).get_item(
                Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})['Item'][
                'collectionStatus']
        next_collection_status = input(
            'Collection Status for collection PIN {} is {}. Enter the desired collection status (START/PAUSE): '.format(
                collection_pin, current_collection_status))
        while next_collection_status != 'START' and next_collection_status != 'PAUSE':
            next_collection_status = input('Invalid input. Enter the desired collection status (START/PAUSE): ')
        self.change_collection_status_given_info(collection_pin, next_collection_status)
        logging.info('Collection Status for collection PIN {} is {}.'.format(collection_pin, next_collection_status))

    def change_collection_status_given_info(self, collection_pin, next_collection_status):
        """
        Change current collection status to desired collection status
        :type collection_pin: String
        :type next_collection_status: String
        """
        if next_collection_status != "START" and next_collection_status != "PAUSE":
            return
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})
        if 'Item' in session:
            current_collection_status = session['Item']['collectionStatus']
            if current_collection_status != "STOP" and current_collection_status != next_collection_status:
                response = table.update_item(
                    Key={
                        utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)
                    },
                    UpdateExpression="SET collectionStatus = :updatedCollectionStatus",
                    ExpressionAttributeValues={':updatedCollectionStatus': next_collection_status}
                )
        return

    @staticmethod
    def ask_collection_goal():
        """
        Ask the user for the desired collection goal
        :return: collection goal
        """
        collection_goal = input('Please enter the collection goal (number >= 1): ')
        while not collection_goal.isdigit() or int(collection_goal) < 1:
            collection_goal = input('Invalid number. Please enter the collection goal (number >= 1): ')
        return int(collection_goal)

    @staticmethod
    def is_number_choice_valid(choice, category_num):
        """
        Check if a user-input index selection is valid

        :param choice: user-input choice
        :param category_num: number of total available choices
        :return: if the user-input choice is valid
        """
        try:
            choice_index = int(choice) - 1
            if choice_index < 0 or choice_index >= category_num:
                raise ValueError
        except ValueError:
            return False
        return True

    @staticmethod
    def collection_request_printer(collection_pin, conversation_pin, mode, collection_info, collection_goal,
                                   collection_status):
        """
        Print out the information of collection request

        :param collection_pin: collection request PIN
        :param conversation_pin: conversation PIN
        :param mode: collection mode
        :param collection_info: collection request information
        """
        logging.info(
            'Your collect request is shown below, please keep the collection request information in a safe place:')
        logging.info('Collection PIN code (Please use it for collecting call recordings): {}'.format(collection_pin))
        logging.info('Conversation PIN code (Please use it for making a conversation): {}'.format(conversation_pin))
        logging.info('Collection Mode: {}'.format(mode))
        logging.info('Collection Goal: {}'.format(collection_goal))
        logging.info('Collection Status: {}'.format(collection_status))
        logging.info('Collection Information: {}'.format(collection_info))
        return
