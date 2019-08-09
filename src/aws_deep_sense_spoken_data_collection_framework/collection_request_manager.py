import logging
import random
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
        self.num_digit_collection_pin = 5
        self.num_digit_conversation_pin = 5
        self.dynamodb = boto3.resource('dynamodb', region_name=self.AWS_REGION_NAME,
                                       aws_access_key_id=self.ACCESS_KEY_ID,
                                       aws_secret_access_key=self.ACCESS_KEY)

    def generate_collect_request(self):
        """
        Generate a new collection request

        """
        try:
            collection_name = self.ask_collection_name()
            is_human_to_human = self.ask_collection_mode()
            collection_goal = self.ask_collection_goal()
            if is_human_to_human:
                mode = 'human'
                if self.get_num_available_queue() == 0:
                    logging.error('Error: No available queue found.')
                else:
                    self.generate_collection_request_given_info(mode, None, collection_goal, collection_name)
            else:
                mode = 'bot'
                bot_info = self.ask_collection_bot()
                self.generate_collection_request_given_info(mode, bot_info, collection_goal, collection_name)
        except Exception as e:
            logging.error('Error: {}'.format(e))
        return

    def generate_collection_request_given_info(self, mode, collection_bot, collection_goal, collection_name):
        """

        :param mode: collection request mode (human2human | human2bot)
        :param collection_bot: lex bot for collection request
        :param collection_goal: number of conversations to be collected in this collection request
        :param collection_name: collection request name
        :return: collection request pin and conversation pin
        """
        collection_pin = self.generate_collection_pin()
        conversation_pin = self.generate_conversation_pin()
        collection_status = 'START'
        if mode == 'human':
            routing_info = {'routingInfo': self.get_routing_info()}
            if 'error' in routing_info['routingInfo']:
                return '', ''
            self.save2db(collection_pin, conversation_pin, mode, routing_info, collection_goal, collection_status,
                         collection_name)
            self.collection_request_printer(collection_pin, conversation_pin, mode,
                                            None, collection_goal, collection_status,
                                            collection_name, [])
        elif mode == 'bot':
            bot_info = {'collectionBot': collection_bot}
            self.save2db(collection_pin, conversation_pin, mode, bot_info, collection_goal, collection_status,
                         collection_name)
            self.collection_request_printer(collection_pin, conversation_pin, mode, bot_info['collectionBot'],
                                            collection_goal, collection_status, collection_name, [])
        return collection_pin, conversation_pin

    def get_routing_info(self):
        """
        Retrieve an available queue from the queue pool
        :return: routing information, including queue id, and routing profile id
        """
        table = self.dynamodb.Table('connectQueuePool')
        available_queue = table.scan(ProjectionExpression='queueNumber')
        num_available_queue = len(available_queue)
        if num_available_queue == 0:
            logging.error('Error: No available queue found.')
            return {'error': 'No available queue found.'}
        queue_number = random.choice(available_queue['Items'])['queueNumber']
        queue_item = table.get_item(Key={'queueNumber': queue_number})['Item']
        table.delete_item(
            Key={
                'queueNumber': queue_number
            }
        )
        return queue_item

    def get_num_available_queue(self):
        """
        Get number of available queues for human/human collection
        :return: number of available queues
        """
        table = self.dynamodb.Table('connectQueuePool')
        available_queue = table.scan(ProjectionExpression='queueNumber')['Items']
        return len(available_queue)

    def generate_collection_pin(self):
        """
        Generate a unique collection PIN code as collection request PIN

        :return: generated 5-digit PIN collection request PIN code
        """
        PIN = utils.random_with_n_digits(self.num_digit_collection_pin)
        while utils.is_collection_pin_exists(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, PIN):
            PIN = utils.random_with_n_digits(self.num_digit_collection_pin)
        return PIN

    def generate_conversation_pin(self):
        """
        Generate a unique 5-digit PIN code as conversation PIN

        :return: generated 5-digit PIN conversation PIN code
        """
        PIN = utils.random_with_n_digits(self.num_digit_conversation_pin)
        while utils.is_conversation_pin_exists(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, PIN):
            PIN = utils.random_with_n_digits(self.num_digit_conversation_pin)
        return PIN

    @staticmethod
    def ask_collection_name():
        """
        Ask the user for the collection request name
        """
        name = input('Collection Request Name (blank for default name): ')
        if len(name) == 0:
            name = 'Default Collection Request Name'
        return name

    @staticmethod
    def ask_collection_mode():
        """
        Ask the user for the desired collection mode

        :return: if the user-selected collection mode is human/human
        """
        print('Please choose among the following collection modes:')
        print('Human/Human - Enter 1')
        print('Human/Bot - Enter 2')
        mode_num = 2
        choice = input('Your choice: ')

        while not utils.is_number_choice_valid(choice, mode_num):
            choice = input('Invalid input. Your choice: ')
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            raise ValueError  # Should not reach here normally

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

        while not utils.is_number_choice_valid(choice, len(session_list)):
            choice = input('Invalid input. Your choice: ')
        choice_index = int(choice) - 1
        collection_bot = session_list[choice_index]['bot']
        return collection_bot

    def get_available_collection_bot(self):
        try:
            bot_table = self.dynamodb.Table('collectionBot')
            bot_list = bot_table.scan()['Items']
            return bot_list
        except Exception as e:
            logging.error('Cannot get available collection bot information from DynamoDB, error: {}'.format(e))
            return []

    def save2db(self, collection_pin, conversation_pin, mode, collection_info, collection_goal, collection_status,
                collection_name):
        """
        Save the collection request information into Dynamo DB

        :param collection_pin: collection request PIN
        :param conversation_pin: conversation PIN
        :param collection_info: human2human: routing info | human2bot: collection bot name
        :param mode: collection request mode
        :param collection_goal: number of conversations to be collected in this collection request
        :param collection_status: START | PAUSE | STOP
        :param collection_name: collection request name

        """
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        with table.batch_writer() as batch:
            collection_item = {utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin,
                               utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY: conversation_pin, 'mode': mode,
                               'contactIDs': [], 'collectionGoal': collection_goal,
                               'collectionStatus': collection_status, 'collectionName': collection_name}
            collection_item.update(collection_info)
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
                                            response['collection_status'], response['collection_name'],
                                            response['contact_ids'])
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
                collection_info = None
            elif mode == 'bot':
                collection_info = session['Item']['collectionBot']
            contact_ids = session['Item']['contactIDs']
            collection_goal = session['Item']['collectionGoal']
            collection_status = session['Item']['collectionStatus']
            collection_name = session['Item']['collectionName']

            response = {'collection_pin': collection_pin, 'conversation_pin': conversation_pin, 'mode': mode,
                        'collection_info': collection_info, 'contact_ids': contact_ids,
                        'collection_goal': collection_goal, 'collection_status': collection_status,
                        'collection_name': collection_name}
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
            collection_name = item['collectionName']
            collection_bot = None
            if mode == 'bot':
                collection_bot = item['collectionBot']
                logging.info(
                    'Collection Name: {}, Collection PIN: {}, conversation PIN: {}, mode: {}, collection bot: {}, collection progress: {}/{}, collection status: {}.'.format(
                        collection_name, collection_pin, conversation_pin, mode, collection_bot, len(contact_ids),
                        collection_goal, collection_status))
            else:
                logging.info(
                    'Collection Name: {}, Collection PIN: {}, conversation PIN: {}, mode: {}, collection progress: {}/{}, collection status: {}.'.format(
                        collection_name, collection_pin, conversation_pin, mode, len(contact_ids),
                        collection_goal, collection_status))
        logging.info('All sessions are listed.')
        return collection_request_list

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
    def collection_request_printer(collection_pin, conversation_pin, mode, collection_bot, collection_goal,
                                   collection_status, collection_name, contact_ids):
        """
        Print out the information of collection request

        :param collection_pin: collection request PIN
        :param conversation_pin: conversation PIN
        :param mode: collection mode
        :param collection_bot: collection request bot for human/bot mode
        :param collection_name: collection request name
        :param contact_ids: list of contact ids (each one represents one conversation)
        """
        logging.info(
            'Your collect request is shown below, please keep the collection request information in a safe place:')
        logging.info('Collection Request Name: {}'.format(collection_name))
        logging.info('Collection PIN code (Please use it for collecting call recordings): {}'.format(collection_pin))
        logging.info('Conversation PIN code (Please use it for making a conversation): {}'.format(conversation_pin))
        logging.info('Collection Mode: {}'.format(mode))
        logging.info('Collection Goal: {}'.format(collection_goal))
        logging.info('Collection Status: {}'.format(collection_status))
        if collection_bot is not None:
            logging.info('Collection Bot: {}'.format(collection_bot))
        logging.info('Collected Conversation:')
        for contact_id in contact_ids:
            logging.info('- Contact ID: {}'.format(contact_id))
        return
