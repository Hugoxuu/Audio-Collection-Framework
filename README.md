# Framework For Spoken and IVR Data Collection

This framework is aimed at collecting Human/Human and Human/Bot conversations through Amazon Connect Services.

## Usages
To run the framework using command line (Support Python3 Only):
```
$ python src/aws_deep_sense_spoken_data_collection_framework/framework_runner.py [-xxx]
```
Usage Summary (**You can only have one operation at a time**) :
```
usage: framework_runner.py [-h] [-sc] [-gc] [-cs] [-lc] [-ec] [-ea] [-cu]
                           [-lu] [-op] [-du] [-da] [-dc] [-gt]

optional arguments:
  -h, --help            show this help message and exit
  -sc, --startCollection
                        start a new collection request
  -gc, --getCollection  get the information of an ongoing collection request
  -cs, --changeCollectionStatus
                        change the collection status of an onging collection
                        request
  -lc, --listCollection
                        list all ongoing collection requests
  -ec, --endCollection  end a collection request, release the resources (Deprecated)
  -ea, --endAllCollection
                        end all collection requests (Deprecated)
  -cu, --createUser     create a new user as conversation role
  -lu, --listAllUser    list all users
  -op, --openConnectPortal
                        open the browser window for Amazon Connect Contact
                        portal
  -du, --deleteUser     delete a user
  -da, --deleteAllUser  delete all users
  -dc, --download       download call recordings and corresponding metadata
                        from AWS S3
  -gt, --getTranscribe  apply machine transcribe to call recordings for fast
                        benchmarking purpose
```
To run the framework using the web interface (Use Django==2.0.7, Support Python3.4+ Only):
```
$ sudo -H pip3 install --upgrade pip;
$ sudo -H pip3 install django==2.0.7;
$ sudo python3 src/ivrFrameworkWebInterface/manage.py runserver
```
Feature Support:  
1. User Management, including:
    * Create a new user (Customer/Agent)
    * Delete a current user
    * List all current users
2. Collection request management, including:
    * Start a new collection request (Human/Human, Human/Bot)
    * Get the information of an ongoing collection request
    * Change the collection status of an onging collection request
    * List all ongoing collection requests
3. Call Recordings Downloading
    * Call recordings (Audio file, lex-bot state file)
    * CTR Metadata (Contact Trace Records)
    * Report for collection requests and conversations

## Details
1. **aws_deep_sense_spoken_data_collection_framework/framework_runner.py**  
    Please use the framework by running this module.  
    This module takes in one command line argument and execute corresponding operations by calling functions in other modules.
2. **aws_deep_sense_spoken_data_collection_framework/call_recordings_manage.py**  
    This module manages call recordings stored in AWS S3, including:
    * Collect call recordings (audio file & meta info) from AWS S3 (PIN code required)
    * Delete call recordings on AWS S3 (PIN code required)
    * Preprocess call recordings (e.g. split the audio file by channel)
    * Apply and download machine transcribe to call recordings on AWS S3 (PIN code required)  
    Unit tests for this module can be found at **aws_deep_sense_spoken_data_collection_framework/test/test_call_recordings_manage.py** 
3. **aws_deep_sense_spoken_data_collection_framework/conversation_manage.py**  
    This module manages the conversation sessions on Amazon Connect and relevant conversation information stored in AWS Dynamo DB, including: 
    * Create a new conversation session, providing:   
        * Unique 5-digit Collection Request PIN code for collection session access
        * Unique 5-digit Conversation PIN code for conversation only
    * Retrieve information of an Ongoing Collection Request (PIN code required), providing:
        * Unique 5-digit Collection Request PIN code for collection session access
        * Unique 5-digit Conversation PIN code for conversation only
        * History of all conversations, along with the JSON metadata
    * List all Ongoing Collection Requests
    * End a Collection Requests, release the resources used by this request, including:
        * Delete call recordings in AWS S3
        * Delete session information in AWS Dynamo DB
        * Delete user account in Amazon Connect
    * End all Collection Requests, free up all resources  
    Unit tests for this module can be found at **aws_deep_sense_spoken_data_collection_framework/test/test_conversation_manage.py** 
4. **aws_deep_sense_spoken_data_collection_framework/user_manage.py**  
    This module manages the user account as conversation roles on Amazon Connect and relevant user information stored in AWS Dynamo DB, including:
    * Create a new user as conversation role, providing:
        * Select between customer and agent conversation role for the user created
        * Unqiue 6-digit User PIN code
        * Account information
            * Customer: external phone number
            * Agent: Amazon Connect user account (username, password), CCP
    * List all users: List all existing user and their basic information
    * Delete a user, including:
        * Customer: Delete user information in AWS Dynamo DB
        * Agent: Delete user information in AWS Dynamo DB, Delete user account in Amazon Connect
    * Delete all existing users
    * Open Amazon Connect Contact Center Portal (PIN code required) for an agent-role user, providing:
        * Open a Chrome browser popup window
        * Retrieve the user account, and auto-login the contact center portal (CCP)  
    Unit tests for this module can be found at **aws_deep_sense_spoken_data_collection_framework/test/test_user_manage.py** 
5. **aws_deep_sense_spoken_data_collection_framework/utils.py**  
    This module provides common methods that will be used among other modules, including:
    * Get parameter from 'aws_config' file, including:
        * AWS Secret Account Key
        * AWS S3 Bucket Name that stores all call recordings
        * AWS Connect Instance Information
    * Methods about PIN, including:
        * Ask for a valid PIN
        * Check if a PIN exists
    * Query information stored in AWS Dynamo DB  
    Unit tests for this module can be found at **aws_deep_sense_spoken_data_collection_framework/test/test_utils.py** 
6. **aws_deep_sense_spoken_data_collection_framework/AWS_lambda_functions.py**  
    This module is not directly run by the framework. It is deployed on AWS and will be called during the conversation.   
7. **aws_deep_sense_spoken_data_collection_framework/configurations/aws_config**  
    This file is a configuration file of the AWS Infrastructure that the platform will be used upon. It is in format of key-pair to store important AWS credentials and parameters.  
    * ACCESS_KEY_ID, ACCESS_KEY: AWS account credentials
    * BUCKET_NAME: AWS S3 Bucket Name for retrieving call recordings
    * CONNECT_INSTANCE_ID: AWS Connect Instance ID
    * CONNECT_SECURITY_ID: AWS Connect Default Security Profile ID for Agent User Account
    * CONNECT_ROUTING_ID: AWS Connect Routing Profile ID
8. **ivrFrameworkWebInterface/views.py**  
    This file consists of groups of individual functions that take a Web request and returns a Web response.
9. **ivrFrameworkWebInterface/templates/\*.html**  
    Template HTML files that will be filled and converted into final HTML page shown to the user by Django view-controller.
10. **ivrFrameworkWebInterface/static/\*file**  
    Static files for the web interface to use, including image files, downloadable files, and CSS files.




