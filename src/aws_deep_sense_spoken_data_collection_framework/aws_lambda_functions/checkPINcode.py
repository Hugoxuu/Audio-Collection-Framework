# check_pin_code_lambda.py: This module is not directly run by the framework.
#                           It is deployed on AWS and will be called during the conversation.
#                           This module is to check if a PIN code, which entered by a customer,
#                           is valid, by querying AWS Dynamo DB.

import os
import json
import boto3
from boto3.dynamodb.conditions import Key

AWS_REGION_NAME = os.environ['AWS_REGION_NAME']
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
DYNAMODB_COLLECTION_REQUEST_TABLE_NAME = 'collectionSession'
DYNAMODB_COLLECTION_REQUEST_SECONDARY_INDEX = 'conversationPIN-index'
HUMAN2HUMAN_MODE = 'human'
HUMAN2BOT_MODE = 'bot'


def check_user_pin(user_pin):
    """
    Check if the user-input user PIN is valid
    :type user_pin: String
    :return: if the PIN is valid
    """
    table = dynamodb.Table('userAccount')
    session = table.get_item(Key={"PIN": str(user_pin)})
    response = {'response': 'False'}
    if 'Item' in session and session['Item']['type'] == 'customer':
        response = {'response': 'True'}
    return response


def check_conversation_pin(conversation_pin, event):
    """
    Check if the user-input conversation PIN is valid
    :type conversation_pin: String
    :return: if the PIN is valid
    """
    table = dynamodb.Table(DYNAMODB_COLLECTION_REQUEST_TABLE_NAME)
    resp = table.query(
        # Add the name of the index you want to use in your query.
        IndexName=DYNAMODB_COLLECTION_REQUEST_SECONDARY_INDEX,
        KeyConditionExpression=Key('conversationPIN').eq(conversation_pin),
    )

    response = dict()
    response['response'] = 'False'
    if resp['Count'] == 1 and resp['Items'][0]['collectionStatus'] == 'START':
        collection_pin = resp['Items'][0]['collectionPIN']
        session = table.get_item(Key={"collectionPIN": collection_pin})
        mode = session['Item']['mode']
        response['response'] = mode

        # Get queue Arn for Human/Human Conversation
        if mode == HUMAN2HUMAN_MODE:
            queue_arn = session['Item']['queueArn']
            response['queueArn'] = queue_arn
        elif mode == HUMAN2BOT_MODE:
            bot = session['Item']['collectionBot']
            response['bot'] = bot

        # Put new contact id into a list that associates with the PIN code
        contact_id = event['Details']['ContactData']['ContactId']
        list_contact_ids = session['Item']['contactIDs']
        list_contact_ids.append(contact_id)
        # Stop the collection if meeting the collection goal
        if len(list_contact_ids) >= session['Item']['collectionGoal']:
            session['Item']['collectionStatus'] = 'STOP'
        table.put_item(Item=session['Item'], ReturnValues='NONE')

    return response


def lambda_handler(event, context):
    if 'userPIN' in event['Details']['Parameters']:
        user_pin = event['Details']['Parameters']['userPIN']
        response = check_user_pin(user_pin)
    elif 'conversationPIN' in event['Details']['Parameters']:
        conversation_pin = event['Details']['Parameters']['conversationPIN']
        response = check_conversation_pin(conversation_pin, event)
    else:
        response = {'response': 'False'}
    print('response: {}'.format(response))
    return response
