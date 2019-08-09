import sys, os, re, json, boto3

sys.path.insert(0, os.path.join('..'))

from django.shortcuts import render, redirect, get_object_or_404, HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.utils.encoding import smart_str
from ivrFrameworkWebInterface.forms import *
from ivrFrameworkWebInterface.models import *

from io import BytesIO
from zipfile import ZipFile
from aws_deep_sense_spoken_data_collection_framework import call_recordings_manager, collection_request_manager, \
    user_manager, utils

# Change to your desired configuration file
config_path = os.path.join('..', '..', 'configurations', 'aws_config_isengard')

ACCESS_KEY_ID, ACCESS_KEY = utils.get_aws_access_key(config_path)
AWS_REGION_NAME = utils.get_aws_region_name(config_path)
CALL_RECORDINGS_BUCKET_NAME = utils.get_call_recordings_bucket_name(config_path)

CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID, CONNECT_PHONE_NUMBER, CONNECT_CCP_URL = utils.get_connect_info(config_path)

user_manager = user_manager.UserManager(config_path, ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                        CONNECT_INSTANCE_ID, CONNECT_SECURITY_ID,
                                        CONNECT_PHONE_NUMBER, CONNECT_CCP_URL)
collection_request_manager = collection_request_manager.CollectionRequestManager(ACCESS_KEY_ID, ACCESS_KEY,
                                                                                 AWS_REGION_NAME,
                                                                                 CALL_RECORDINGS_BUCKET_NAME)
call_recordings_manager = call_recordings_manager.CallRecordingsManager(ACCESS_KEY_ID, ACCESS_KEY, AWS_REGION_NAME,
                                                                        CALL_RECORDINGS_BUCKET_NAME)


def login_action(request):
    context = {}
    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = LoginForm()
        return render(request, 'ivrFrameworkWebInterface/login.html', context)

    # Check post error
    error_list = []
    if (not 'username' in request.POST) or (request.POST['username'] == ""):
        error_list.append("Miss username")
    if (not 'password' in request.POST) or (request.POST['password'] == ""):
        error_list.append("Miss password")
    if len(error_list) > 0:
        context['error_list'] = error_list
        return render(request, 'ivrFrameworkWebInterface/login.html', context)

    # Creates a bound form from the request POST parameters
    info = {
        'username': request.POST['username'],
        'password': request.POST['password']
    }

    form = LoginForm(info)

    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        error_list.append("Invalid username/password")
        return render(request, 'ivrFrameworkWebInterface/login.html', context)

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)

    return redirect(reverse('homepage'))


@login_required
def logout_action(request):
    logout(request)
    return redirect(reverse('login'))


@login_required
def homepage(request):
    context = {}
    return render(request, 'ivrFrameworkWebInterface/homepage.html', context)


@login_required
def user_manage_action(request):
    context = {}

    if request.method == 'POST':
        error_list = []
        response_list = {}
        if 'new_user_role' in request.POST and 'new_user_name' in request.POST:
            role = request.POST['new_user_role']
            name = request.POST['new_user_name']
            if role == 'customer' or role == 'agent':
                if role == 'customer':
                    user_pin, user_account = user_manager.create_user_given_info(role, name, '')
                elif role == 'agent':
                    collection_pin = request.POST['new_user_collection_pin']
                    if collection_pin == 'not_selected':
                        error_list.append('Invalid collection request input.')
                    else:
                        user_pin, user_account = user_manager.create_user_given_info(role, name, collection_pin)
                        response_list['new_user_collection_pin'] = collection_pin
                if len(error_list) == 0:
                    response_list['new_user_role'] = role
                    response_list['new_user_pin'] = user_pin
                    response_list['new_user_name'] = name
            else:
                error_list.append('Invalid user role input.')
        if 'delete_user_pin' in request.POST:
            user_pin = request.POST['delete_user_pin']
            delete_error_list = user_manager.delete_user_given_pin(user_pin)
            if len(delete_error_list) == 0:
                response_list['delete_user_pin'] = user_pin
            else:
                for error in delete_error_list:
                    error_list.append(error)

        context['error_list'] = error_list
        context['response_list'] = response_list

    context['collection_request_list'] = user_manager.list_collection_request_option()
    context['user_list'] = user_manager.list_all_user()
    context['amazon_connect_phone_number'] = user_manager.get_phone_number()
    context['amazon_connect_ccp_link'] = user_manager.get_URL()
    return render(request, 'ivrFrameworkWebInterface/user_manage.html', context)


@login_required
def collection_request_action(request):
    context = {}
    error_list = []

    if request.method == 'POST':
        if ('human2human_collection_name' in request.POST and 'human2human_collection_goal' in request.POST) or (
                'human2bot_collection_name' in request.POST and 'new_human2bot_collection_category' in request.POST and 'human2bot_collection_goal' in request.POST):

            collection_bot = ''
            mode = 'human'
            if 'new_human2bot_collection_category' in request.POST:
                collection_bot = request.POST['new_human2bot_collection_category']
                mode = 'bot'

            new_collection_request = {}
            if mode == 'bot':
                if collection_bot != 'Choose a bot...':
                    new_collection_request['collection_bot'] = collection_bot
                else:
                    error_list.append('Invalid Collection Category.')

            collection_goal = -1
            if 'human2human_collection_goal' in request.POST:
                collection_goal = parse_positive_int_without_exception(request.POST['human2human_collection_goal'])
                if collection_goal > 0:
                    new_collection_request['collection_goal'] = collection_goal
                else:
                    error_list.append('Invalid Collection Goal.')

            if 'human2bot_collection_goal' in request.POST:
                collection_goal = parse_positive_int_without_exception(request.POST['human2bot_collection_goal'])
                if collection_goal > 0:
                    new_collection_request['collection_goal'] = collection_goal
                else:
                    error_list.append('Invalid Collection Goal.')

            collection_name = ''
            if 'human2human_collection_name' in request.POST:
                collection_name = request.POST['human2human_collection_name']
            if 'human2bot_collection_name' in request.POST:
                collection_name = request.POST['human2bot_collection_name']
            if len(collection_name) == 0:
                collection_name = 'Default Collection Request Name'

            if len(error_list) == 0:
                collection_pin, conversation_pin = collection_request_manager.generate_collection_request_given_info(
                    mode, collection_bot, collection_goal, collection_name)
                new_collection_request.update(
                    {'collection_pin': collection_pin, 'conversation_pin': conversation_pin, 'mode': mode,
                     'collection_name': collection_name})
                context['new_collection_request'] = new_collection_request
        elif 'get_collection_pin' in request.POST:
            collection_pin = request.POST['get_collection_pin']
            get_collection_pin_response = collection_request_manager.get_collection_request_given_pin(collection_pin)
            transcribe = boto3.client('transcribe', aws_access_key_id=ACCESS_KEY_ID,
                                      aws_secret_access_key=ACCESS_KEY)
            contact_ids = get_collection_pin_response['contact_ids']
            contact_ids_transcribe_status = {}
            for contact_id in contact_ids:
                transcribe_status = call_recordings_manager.check_transcribe_given_contact_id(transcribe, contact_id)
                contact_ids_transcribe_status[contact_id] = transcribe_status
            if len(contact_ids) == 0:
                get_collection_pin_response['contact_ids'] = {}
            else:
                get_collection_pin_response['contact_ids'] = contact_ids_transcribe_status
            context['get_collection_pin_response'] = get_collection_pin_response

    bot_list = collection_request_manager.get_available_collection_bot()
    context['bot_list'] = bot_list
    context['collection_request_list'] = collection_request_manager.list_collect_requests()
    context['num_available_queue'] = collection_request_manager.get_num_available_queue()

    context['error_list'] = error_list
    return render(request, 'ivrFrameworkWebInterface/collection_request.html', context)


@login_required
def download_call_recordings(request):
    if request.method == 'GET':
        return

    collection_pin = request.POST['collectionPIN']
    static_file_path = os.path.join('ivrFrameworkWebInterface','static', 'callRecordings')

    output_file_path = os.path.join(static_file_path, collection_pin)
    call_recordings_manager.download_call_recordings_given_pin(collection_pin, output_file_path)

    # crawling through directory and subdirectories
    filenames = []
    for root, directories, files in os.walk(output_file_path):
        for filename in files:
            # join the two strings in order to form the full filepath. 
            filepath = os.path.join(root, filename)
            filenames.append(filepath)

    if len(filenames) == 0:
        return HttpResponse(status=204)
    # Open BytesIO to grab in-memory ZIP contents
    s = BytesIO()
    zip_file_object = ZipFile(s, 'w')
    zip_dir = 'call_recordings_{}'.format(collection_pin)
    for fpath in filenames:
        # Calculate path for file in zip
        fdir, fname = os.path.split(fpath)
        # Add file, at correct path
        zip_subdir = fdir[len(static_file_path) + 1:]
        zip_path = os.path.join(zip_dir, zip_subdir, fname)
        zip_file_object.write(fpath, zip_path)
    # Must close zip for all contents to be written
    zip_file_object.close()

    # Grab ZIP file from in-memory, make response with correct MIME-type
    response = HttpResponse(s.getvalue(), content_type='application/x-zip-compressed')
    response['Content-Disposition'] = 'attachment; filename=%s' % '{}.zip'.format(zip_dir)
    return response


@login_required
def transcribe_job_request(request):
    if request.method == 'GET':
        return
    transcribe = boto3.client('transcribe', aws_access_key_id=ACCESS_KEY_ID,
                              aws_secret_access_key=ACCESS_KEY)
    response = HttpResponse()
    if 'download_contact_id' in request.POST:
        contact_id = request.POST['download_contact_id']
        response = transcribe.get_transcription_job(TranscriptionJobName=contact_id)
        transcript_file_url = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
        return HttpResponseRedirect(transcript_file_url)
    if 'start_contact_id' in request.POST:
        contact_id = request.POST['start_contact_id']
        if not call_recordings_manager.start_transcribe_job(transcribe, 'human', contact_id):
            call_recordings_manager.start_transcribe_job(transcribe, 'bot', contact_id)
        return HttpResponse(status=204)


@login_required
def about_action(request):
    context = {}
    return render(request, 'ivrFrameworkWebInterface/about.html', context)


@login_required
def change_collection_status(request):
    if request.method == 'GET':
        return
    collection_pin = request.POST['collection_pin']
    next_collection_status = request.POST['next_collection_status']
    collection_request_manager.change_collection_status_given_info(collection_pin, next_collection_status)
    return HttpResponse(status=204)


def parse_positive_int_without_exception(number):
    try:
        return int(number)
    except ValueError:
        return 0
