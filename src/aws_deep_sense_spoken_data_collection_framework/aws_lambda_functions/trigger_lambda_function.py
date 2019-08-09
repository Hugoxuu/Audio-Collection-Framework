"""
trigger_lambda_function.py:
Forward the parameters from Amazon Connect and
Trigger another lambda function which does Kinesis Video Streaming Parsing.

"""

import json
import boto3
import logging

HTTP_RESPONSE_SUCCESS_CODE = 200
KVS_PARSER_LAMBDA_FUNCTION = 'KVSTranscribeStreamingLambda'


def lambda_handler(event, context):
    """
    The caller function of the lambda function
    :param event: event-specified information, type: dict
    :param context: context information (Not used)
    :return: response dict
    """
    logging.info(event)
    output_event = dict()
    output_event['streamARN'] = event['Details']['ContactData']['MediaStreams']['Customer']['Audio']['StreamARN']
    output_event['startFragmentNum'] = event['Details']['ContactData']['MediaStreams']['Customer']['Audio'][
        'StartFragmentNumber']
    output_event['connectContactId'] = event['Details']['ContactData']['ContactId']
    output_event['transcriptionEnabled'] = 'false'
    output_event['saveCallRecording'] = 'true'
    output_event['languageCode'] = 'en-US'

    lambda_client = boto3.client('lambda')
    invoke_response = lambda_client.invoke(FunctionName=KVS_PARSER_LAMBDA_FUNCTION,
                                           InvocationType='Event',
                                           Payload=json.dumps(output_event))
    response = {
        'statusCode': HTTP_RESPONSE_SUCCESS_CODE,
        'body': json.dumps('Success')
    }
    logging.info(response)
    return response
