import os
import json
import logging
import boto3
import urllib.request
import scipy.io.wavfile as wavfile
import aws_deep_sense_spoken_data_collection_framework.utils as utils
import datetime

TRANSCRIBE_JOB_STATUS_NOT_START = 'NOT_STARTED'
TRANSCRIBE_JOB_STATUS_IN_PROGRESS = 'IN_PROGRESS'
TRANSCRIBE_JOB_STATUS_COMPLETED = 'COMPLETED'
TRANSCRIBE_JOB_STATUS_FAILED = 'FAILED'
TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
AUDIO_MEDIA_SAMPLE_RATE_HERTZ = 8000
MINIMUM_SILENCE_LENGTH_MS = 2000
SILENCE_THRESHOLD_DB = -60


class CallRecordingsManager:
    """
    A module class for managing call recordings stored in AWS S3, along with the metadata associated with it.

    :param ACCESS_KEY_ID: Access credential key id for AWS account
    :param ACCESS_KEY: Access Credential key for AWS account
    :param AWS_REGION_NAME: Region name for AWS services
    :param CALL_RECORDINGS_BUCKET_NAME: AWS S3 bucket name for storing the call recordings
    """

    def __init__(self, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME, CALL_RECORDINGS_BUCKET_NAME):
        self.ACCESS_KEY_ID = ACCESS_KEY_ID
        self.ACCESS_KEY = ACCESS_KEY
        self.AWS_REGION_NAME = AWS_REGION_NAME
        self.CALL_RECORDINGS_BUCKET_NAME = CALL_RECORDINGS_BUCKET_NAME

        self.dynamodb = boto3.resource('dynamodb', region_name=self.AWS_REGION_NAME,
                                       aws_access_key_id=self.ACCESS_KEY_ID,
                                       aws_secret_access_key=self.ACCESS_KEY)
        self.s3_resource = boto3.resource('s3', aws_access_key_id=self.ACCESS_KEY_ID,
                                          aws_secret_access_key=self.ACCESS_KEY)
        self.s3_client = boto3.client('s3', aws_access_key_id=self.ACCESS_KEY_ID,
                                      aws_secret_access_key=self.ACCESS_KEY)

    def download_call_recordings(self):
        """
        Download call recordings in AWS S3 given a valid collection PIN code

        """
        collection_pin = utils.ask_collection_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        output_file_path = self.ask_output_directory(collection_pin)
        self.download_call_recordings_given_pin(collection_pin, output_file_path)

        decision = input(
            'Apply AWS Transcribe jobs to call recordings for fast benchmarking purpose? Y/N | ')
        if decision == 'Y' or decision == 'y':
            self.get_transcribe_given_pin(collection_pin, output_file_path)
        return

    def download_call_recordings_given_pin(self, collection_pin, output_file_path):
        """
        Download call recordings in AWS S3 given a valid collection PIN code, and a valid output file path
        :param collection_pin: 5-digit collection PIN code
        :param output_file_path: Output file path for call recordings
        """
        self.ensure_directory_exists(output_file_path)

        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: collection_pin})
        mode = session['Item']['mode']

        # Retrieve all call recording files under the user S3 bucket
        call_recordings_bucket = self.s3_resource.Bucket(self.CALL_RECORDINGS_BUCKET_NAME)
        list_ids = utils.get_contact_ids(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, collection_pin)

        # Download bot definition if human/bot
        if mode == 'bot':
            bot_name = session['Item']['collectionBot']
            self.download_bot_definition(bot_name, output_file_path)

        # Download call recordings per contact id
        counter = 0  # Count the number of conversations downloaded
        for contact_id in list_ids:
            try:
                output_file_path_with_contact_id = os.path.join(output_file_path, contact_id)
                self.ensure_directory_exists(output_file_path_with_contact_id)  # Ensure the file path exists
                if len(os.listdir(output_file_path_with_contact_id)) == 0:  # Not downloaded before
                    key_prefix = contact_id + '/'
                    objects_with_contact_id = call_recordings_bucket.objects.filter(Prefix=key_prefix)
                    for objects_with_contact_id in objects_with_contact_id:
                        object_key = objects_with_contact_id.key
                        s3_file_name = object_key.split('/', 1)[-1]
                        output_file_name = os.path.join(output_file_path_with_contact_id, s3_file_name)
                        call_recordings_bucket.download_file(object_key, output_file_name)
                    if mode == 'human':
                        call_recordings_output_file_name = os.path.join(output_file_path_with_contact_id,
                                                                        'call_recordings_{}.wav'.format(contact_id))
                        if os.path.exists(call_recordings_output_file_name) and os.path.isfile(
                                call_recordings_output_file_name):
                            self.split_audio_by_channel(call_recordings_output_file_name)
                    if mode == 'bot':
                        self.split_audio_by_lex_bot_state(output_file_path_with_contact_id, contact_id)
                    counter += 1
                self.generate_conversation_report(mode, contact_id, output_file_path_with_contact_id)
            except Exception as e:
                logging.error('Download Failure with Contact ID {}, Error Message: {}'.format(contact_id, e))
        logging.info('Download Success, {} Conversations are Downloaded Under "{}" Directory.'.format(counter,
                                                                                                      output_file_path))

        if len(list_ids) != 0:
            self.generate_collection_request_report(collection_pin, output_file_path)
            self.get_transcribe_given_pin(collection_pin, output_file_path)
        return

    def download_bot_definition(self, bot_name, output_file_path):
        bot_definition_zip_path = os.path.join(output_file_path, 'bot_definition_{}.zip'.format(bot_name))

        if not os.path.exists(bot_definition_zip_path):
            try:
                lex_model = boto3.client('lex-models', region_name=self.AWS_REGION_NAME,
                                         aws_access_key_id=self.ACCESS_KEY_ID,
                                         aws_secret_access_key=self.ACCESS_KEY)
                response = lex_model.get_export(
                    name=bot_name,
                    version='1',
                    resourceType='BOT',
                    exportType='LEX'
                )
                bot_definition_url = response['url']
                urllib.request.urlretrieve(bot_definition_url, bot_definition_zip_path)
            except Exception as e:
                logging.error('Cannot download bot definition for {}, Error: {}'.format(bot_name, e))

    def get_transcribe(self):
        """
        Get text transcribe of previous call recordings from AWS Transcribe
        """
        collection_pin = utils.ask_collection_pin(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME)
        output_file_path = self.ask_output_directory(collection_pin)
        self.get_transcribe_given_pin(collection_pin, output_file_path)

    def get_transcribe_given_pin(self, collection_pin, output_file_path):
        """
        Get text transcribe of previous call recordings from AWS Transcribe given collection PIN and output file path

        :param collection_pin: collection session PIN
        :param output_file_path: the output file path for transcribe file downloaded
        """
        transcribe = boto3.client('transcribe', aws_access_key_id=self.ACCESS_KEY_ID,
                                  aws_secret_access_key=self.ACCESS_KEY)
        list_ids = utils.get_contact_ids(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, collection_pin)
        mode = utils.check_collection_request_mode(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME,
                                                   collection_pin)
        for contact_id in list_ids:
            job_status = self.check_transcribe_given_contact_id(transcribe, contact_id)

            if job_status == TRANSCRIBE_JOB_STATUS_IN_PROGRESS:
                logging.info('Transcribe job with contact id {} is in progress.'.format(contact_id))
            elif job_status == TRANSCRIBE_JOB_STATUS_FAILED:
                logging.info('Transcribe job with contact id {} is failed.'.format(contact_id))
            elif job_status == TRANSCRIBE_JOB_STATUS_COMPLETED:
                response = transcribe.get_transcription_job(TranscriptionJobName=contact_id)
                transcript_file_url = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                #  Download the transcribe file
                output_file_path_with_contact_id = os.path.join(output_file_path, contact_id)
                self.ensure_directory_exists(output_file_path_with_contact_id)
                output_transcribe_file_name = os.path.join(output_file_path_with_contact_id,
                                                           'transcribe_{}.json'.format(contact_id))
                if not os.path.exists(output_transcribe_file_name):
                    transcribe_json = urllib.request.urlopen(transcript_file_url).read()
                    transcribe_dict = json.loads(transcribe_json)
                    with open(output_transcribe_file_name, 'w+') as transcript_file:
                        transcript_file.write(str(json.dumps(transcribe_dict, indent=4, sort_keys=True)))
                    logging.info('Transcribe job with contact id {} is downloaded.'.format(contact_id))
            elif job_status == TRANSCRIBE_JOB_STATUS_NOT_START:
                # Start Transcribe job on AWS Transcribe with the one not in S3
                if self.start_transcribe_job(transcribe, mode, contact_id):
                    logging.info('Transcribe job with contact id {} is in progress.'.format(contact_id))
                else:
                    logging.error(
                        'Transcribe job with contact id {} is failed. Cannot find S3 audio file.'.format(contact_id))

    def start_transcribe_job(self, transcribe_object, mode, contact_id):
        """
        Start the transcribe job
        :param transcribe_object: AWS Transcribe Object
        :param mode: Collection Request Mode
        :param contact_id: Contact ID to start Transcribe
        :return: If the job is successfully started
        """
        file_prefix = 'call_recordings' if mode == 'human' else 'customer'
        s3_audio_file_key = '{}/{}_{}.wav'.format(contact_id, file_prefix, contact_id)
        try:
            response = transcribe_object.start_transcription_job(
                TranscriptionJobName=contact_id,
                LanguageCode='en-US',
                MediaSampleRateHertz=AUDIO_MEDIA_SAMPLE_RATE_HERTZ,
                MediaFormat='wav',
                Media={
                    'MediaFileUri': 'https://s3-{}.amazonaws.com/{}/{}'.format(self.AWS_REGION_NAME,
                                                                               self.CALL_RECORDINGS_BUCKET_NAME,
                                                                               s3_audio_file_key)
                },
                Settings={
                    'ChannelIdentification': True
                }
            )
            return True
        except:
            return False

    def delete_call_recordings_given_pin(self, collection_pin):
        """
        Delete call recordings in AWS S3 given a valid collection PIN code

        :param collection_pin: collection request PIN code associated with the call recordings
        """
        bucket = self.s3_resource.Bucket(self.CALL_RECORDINGS_BUCKET_NAME)
        list_ids = utils.get_contact_ids(self.ACCESS_KEY_ID, self.ACCESS_KEY, self.AWS_REGION_NAME, collection_pin)
        for s3_file in bucket.objects.all():
            key = s3_file.key
            contact_id = self.parse_contact_id_from_key(key)  # Parse the contact ID from file key
            # Only Download audio files associated with the PIN code
            if contact_id in list_ids:
                if s3_file.size != 0:
                    response = bucket.delete_objects(
                        Delete={
                            'Objects': [
                                {
                                    'Key': key
                                },
                            ],
                            'Quiet': True
                        }
                    )
        return

    @staticmethod
    def ask_output_directory(pin):
        """
        Ask the user for the output file directory

        :param pin: collection request PIN for the convenience of naming file path
        :return: the final file path
        """
        default_path = os.path.join(os.getcwd(), 'audio_file')
        file_path = input('Enter Output File Directory (blank for {}): '.format(default_path))
        if len(file_path) == 0 or not os.path.exists(file_path):  # Default Setting
            file_path = os.path.join(default_path, pin)
        else:
            file_path = os.path.abspath(file_path)
            file_path = os.path.join(file_path, pin)

        return file_path

    @staticmethod
    def ensure_directory_exists(file_path):
        """
        Ensure the directory exists, create one if not exists

        :param file_path: the file path to create if not exists
        """
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        return

    @staticmethod
    def parse_contact_id_from_key(key):
        """
        Parse the contact ID from S3 file key (only for auto-saved Amazon Connect Audio File)

        :param key: The S3 file key
        :return: parsed contact ID
        """
        contact_id = key.split('/')[-1].split('_')[0]
        return contact_id

    @staticmethod
    def split_audio_by_channel(audio_file):
        """
        Separate the customer-agent dialog audio file into 2 files by channel
        one for customer-only audio, one for agent-only audio
        1. parse the file name
        2. read the file
        3. save first column which corresponds to channel 1
        4. save second column which corresponds to channel 2

        :param audio_file: path for the audio file
        """

        audio_file_name = audio_file.split('.')[0]
        fs, data = wavfile.read(audio_file)
        wavfile.write('{}_customer.wav'.format(audio_file_name), fs, data[:, 0])
        wavfile.write('{}_agent.wav'.format(audio_file_name), fs, data[:, 1])

    def split_audio_by_lex_bot_state(self, output_file_path_with_contact_id, contact_id):
        """
        Split the human/bot customer audio depending on the lex bot timestamp.
        Will detect only the non-silent part and can handle
        :type output_file_path_with_contact_id: str
        :type contact_id: str
        """
        # Import package here to avoid overhead when creating class object
        from pydub.silence import detect_nonsilent
        from pydub import AudioSegment

        ctr_file_name = os.path.join(output_file_path_with_contact_id, 'ctr_{}.json'.format(contact_id))
        with open(ctr_file_name, 'r') as ctr_file:
            ctr_json = json.load(ctr_file)
            start_timestamp = ctr_json['Recordings'][0]['StartTimestamp']

        lex_bot_file_name = os.path.join(output_file_path_with_contact_id, 'lex_bot_{}.json'.format(contact_id))
        with open(lex_bot_file_name, 'r') as lex_bot_file:
            time_response_list = []
            lex_bot_json = json.load(lex_bot_file)
            for turn in lex_bot_json['conversationHistory']:
                time_response_list.append(turn['timestamp'])
            logging.info(time_response_list)

        lex_response_timestamps = []
        for time_response in time_response_list:
            relative_time = datetime.datetime.strptime(time_response, TIMESTAMP_FORMAT) - datetime.datetime.strptime(
                start_timestamp,
                TIMESTAMP_FORMAT)
            lex_response_timestamps.append(relative_time.seconds * 1000)  # pydub time in ms

        logging.info(lex_response_timestamps)

        wav_file_path = os.path.join(output_file_path_with_contact_id, 'customer_{}.wav'.format(contact_id))
        wav_file = AudioSegment.from_wav(wav_file_path)

        chunks = detect_nonsilent(wav_file, min_silence_len=MINIMUM_SILENCE_LENGTH_MS,
                                  silence_thresh=SILENCE_THRESHOLD_DB)
        chunks.append([lex_response_timestamps[-1] + 1])
        if len(chunks) != len(lex_response_timestamps):
            valid_chunks = []
            chunks_index = 1
            for timestamp in lex_response_timestamps:
                while chunks_index < len(chunks):
                    if chunks[chunks_index][0] > timestamp:
                        if chunks[chunks_index - 1] in valid_chunks:
                            # No sound found during this period, make up a silent one
                            previous_end_point = chunks[chunks_index - 1][1]
                            valid_chunks.append([previous_end_point + 1, previous_end_point + 2])
                        else:
                            valid_chunks.append(chunks[chunks_index - 1])
                        break
                    chunks_index += 1
        else:
            valid_chunks = chunks

        logging.info('Valid chunks: {}'.format(valid_chunks))
        chunk_output_file_path = os.path.join(output_file_path_with_contact_id, 'audio_chunks')
        self.ensure_directory_exists(chunk_output_file_path)
        silence_chunk = AudioSegment.silent(duration=500)
        for i, chunk in enumerate(valid_chunks):
            audio_chunk = wav_file[chunk[0]:chunk[1]]
            audio_chunk = silence_chunk + audio_chunk + silence_chunk
            chunk_file_path = os.path.join(chunk_output_file_path,
                                           'chunk{}_customer_{}.wav'.format(i, contact_id))
            audio_chunk.export(chunk_file_path, format='wav')
        return

    def generate_collection_request_report(self, collection_pin, output_file_path):
        """
        Generate a report for one collection request

        :param collection_pin: collection request PIN
        :param output_file_path: the output file path for transcribe file downloaded
        """

        # Get all requests from the table
        table = self.dynamodb.Table(utils.COLLECTION_REQUEST_DYNAMODB_TABLE)
        session = table.get_item(Key={utils.COLLECTION_REQUEST_DYNAMODB_TABLE_KEY: str(collection_pin)})
        if 'Item' in session:
            item = session['Item']
            collection_pin = item['collectionPIN']
            contact_ids = item['contactIDs']
            conversation_pin = item[utils.COLLECTION_REQUEST_DYNAMODB_SECONDARY_INDEX_KEY]
            mode = item['mode']
            collection_goal = item['collectionGoal']
            collection_status = item['collectionStatus']

            collection_type = ''
            if mode == 'human':
                collection_type = item['routingInfo']
            elif mode == 'bot':
                collection_type = item['collectionBot']

            report_output_file_name = os.path.join(output_file_path,
                                                   'collection_request_report_{}'.format(collection_pin))
            with open(report_output_file_name, 'w+') as report_file:
                content = 'Collection PIN: {}\nConversation PIN: {}\nMode: {}\nCategory: {}\nCollection Status: {}\n'.format(
                    collection_pin,
                    conversation_pin,
                    mode,
                    collection_type,
                    collection_status)
                report_file.write(content)
                content = '{}/{} conversation(s) are collected so far:\n'.format(len(contact_ids), collection_goal)
                for index, contact_id in enumerate(contact_ids, start=1):
                    content += '\t{}: {}\n'.format(index, contact_id)
                report_file.write(content)

    @staticmethod
    def generate_conversation_report(mode, contact_id, contact_id_file_path):
        """
        Generate a report for one conversation

        :param mode: Conversation Mode, can be Human/Human or Human/Bot
        :param contact_id: contact id associated with the single call recording
        :param contact_id_file_path: the output file path for downloading
        """
        ctr_file_name = os.path.join(contact_id_file_path, 'ctr_{}.json'.format(contact_id))
        try:
            with open(ctr_file_name, 'r') as json_file:
                ctr_json_dict = json.load(json_file)
        except Exception as e:
            logging.error('Cannot generate report without CTR. Error: {}'.format(e))
            return
        if mode == 'bot':
            lex_bot_file_name = os.path.join(contact_id_file_path, 'lex_bot_{}.json'.format(contact_id))
            try:
                with open(lex_bot_file_name, 'r') as json_file:
                    lex_bot_json_dict = json.load(json_file)
                    bot_conversation_result = lex_bot_json_dict['conversationResult']
            except Exception as e:
                logging.error('Cannot generate report without Lex Bot conversations.  Error: {}'.format(e))
                return

        customer_pin = ctr_json_dict['Attributes']['customerPin']
        agent_pin = ctr_json_dict['Agent']['Username'].split('_')[1] if mode == 'human' else ''
        report_file_name = os.path.join(contact_id_file_path, 'conversation_report_' + contact_id)
        with open(report_file_name, 'w+') as report_file:
            report_file.write('Contact ID: {}\n'.format(contact_id))
            report_file.write('Conversation Mode: human/{}\n'.format(mode))
            report_file.write('Customer PIN: {}\n'.format(customer_pin))
            if mode == 'human':
                report_file.write('Agent PIN: {}\n'.format(agent_pin))
            elif mode == 'bot':
                report_file.write('Conversation Result: {}\n'.format(bot_conversation_result))

    @staticmethod
    def check_transcribe_given_contact_id(transcribe_object, contact_id):
        """
        Check the transcribe job status
        :param transcribe_object: AWS Transcribe Ojbect
        :param contact_id: Contact ID to check transcribe job
        :return: "NOT_STARTED" | "IN_PROGRESS" | "FAILED" | "COMPLETED"
        """
        try:
            transcribe_job_name = contact_id
            response = transcribe_object.get_transcription_job(
                TranscriptionJobName=transcribe_job_name
            )
            job_status = response['TranscriptionJob']['TranscriptionJobStatus']
        except:
            job_status = TRANSCRIBE_JOB_STATUS_NOT_START

        return job_status
