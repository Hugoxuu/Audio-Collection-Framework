"""
Store Lex Bot States and conversation results into Dynamo DB

"""

import json
import boto3
import os
import datetime

s3_resource = boto3.resource('s3')
s3_client = boto3.client('s3')
CALL_RECORDINGS_BUCKET_NAME = os.environ['CALL_RECORDINGS_BUCKET_NAME']


def combine_bot_state_to_s3(event, current_time):
    contact_id = event['Details']['Parameters']['contactId']
    conversation_result = event['Details']['Parameters']['result']
    key_prefix = os.path.join(contact_id, 'lex_bot_{}'.format(contact_id))
    response = s3_client.list_objects(
        Bucket=CALL_RECORDINGS_BUCKET_NAME,
        Prefix=key_prefix
    )
    if 'Contents' in response:
        num_bot_state = len(response['Contents'])
    else:
        num_bot_state = 0

    json_dict = {'conversationResult': conversation_result, 'conversationHistory': [], 'finishedTimestamp': current_time}
    for sequence_number in range(num_bot_state):
        object_key = '{}_{}'.format(key_prefix, sequence_number)
        s3_object = s3_client.get_object(Bucket=CALL_RECORDINGS_BUCKET_NAME, Key=object_key)
        object_content = s3_object['Body'].read()
        json_object = json.loads(object_content)
        json_dict['conversationHistory'].append(json_object)
        s3_resource.Object(CALL_RECORDINGS_BUCKET_NAME, object_key).delete()


    object_key = '{}.json'.format(key_prefix)
    s3_object = s3_resource.Object(CALL_RECORDINGS_BUCKET_NAME, object_key)
    s3_object.put(Body=json.dumps(json_dict, indent=4, sort_keys=True))


def save_bot_state_to_s3(event, current_time):
    contact_id = event['sessionAttributes']['contactId']
    json_dict = event  # Shall save every information from Lex
    json_dict['timestamp'] = current_time
    key_prefix = os.path.join(contact_id, 'lex_bot_{}'.format(contact_id))
    response = s3_client.list_objects(
        Bucket=CALL_RECORDINGS_BUCKET_NAME,
        Prefix=key_prefix
    )
    if 'Contents' in response:
        sequence_number = len(response['Contents'])
    else:
        sequence_number = 0

    object_key = '{}_{}'.format(key_prefix, sequence_number)
    s3_object = s3_resource.Object(CALL_RECORDINGS_BUCKET_NAME, object_key)
    s3_object.put(Body=json.dumps(json_dict))


def lambda_handler(event, context):
    current_time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(current_time)
    print(event)
    is_conversation_result = 'Details' in event
    if is_conversation_result:
        combine_bot_state_to_s3(event, current_time)
    else:
        save_bot_state_to_s3(event, current_time)

    # Generate response back to bot
    response = dict()
    if not is_conversation_result:
        response = {
            'dialogAction': {
                'type': 'Delegate',
                'slots': event['currentIntent']['slots']
            }
        }
    return response
