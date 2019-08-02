"""
Contact Trace Record (CTR): A metadata file that Amazon Connect generates per phone call
Consume the CTR Stream from Kinesis Data Stream and save it into S3 in certain format

"""

import json
import base64
import boto3
import os

s3 = boto3.resource('s3')
CALL_RECORDINGS_BUCKET_NAME = os.environ['CALL_RECORDINGS_BUCKET_NAME']


def transfer_call_recordings(json_dict):
    contact_id = json_dict['ContactId']
    file_name = 'call_recordings_{}.wav'.format(contact_id)
    new_file_key = os.path.join(contact_id, file_name)
    # Copy new files from old files
    s3.Object(CALL_RECORDINGS_BUCKET_NAME, new_file_key).copy_from(CopySource=json_dict['Recording']['Location'])
    # Delete old files
    split_results = json_dict['Recording']['Location'].split('/', 1)
    old_bucket = split_results[0]
    old_file_key = split_results[1]
    s3.Object(old_bucket, old_file_key).delete()


def lambda_handler(event, context):
    for record in event['Records']:
        # Decode CTR using base64, which is the Kinesis data encode rule.
        json_dict = json.loads(base64.b64decode(record["kinesis"]["data"]))
        # transfer call recordings if it is Human/Human
        if json_dict['Agent'] is not None:
            transfer_call_recordings(json_dict)

        contact_id = json_dict['ContactId']
        file_name = 'ctr_{}.json'.format(contact_id)
        object_key = os.path.join(contact_id, file_name)
        # Put CTR into S3 bucket
        s3_object = s3.Object(CALL_RECORDINGS_BUCKET_NAME, object_key)
        s3_object.put(Body=json.dumps(json_dict, indent=4, sort_keys=True))

    response = {'response': 'success'}
    return response
