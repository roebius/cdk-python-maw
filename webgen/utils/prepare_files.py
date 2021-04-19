import sys
import boto3
from botocore.exceptions import ClientError
import os

# Used below in prepare_xray_file, that will replace it in the placeholder in xray_stack.py.
# If the address is not replaced with a valid one the XRay stack deployment will fail.
# receiver_email = 'the_receiver_email@that_provider.com'
receiver_email = os.environ.get('RECEIVER_EMAIL', None)


def get_execute_api_endpoint(api_name, region):

    client = boto3.client('apigateway', region_name=region)

    try:
        api_id = None
        execute_api_prod_endpoint = None
        response = client.get_rest_apis()
        for api in response['items']:
            if api['name'] == api_name:
                api_id = api['id']
        if api_id:
            execute_api_prod_endpoint = 'https://' + api_id + '.execute-api.' + region + '.amazonaws.com/prod'
        return execute_api_prod_endpoint
    except ClientError as e:
        raise e


def get_user_pool_id(user_pool_name, region):

    client = boto3.client('cognito-idp')

    try:
        user_pool_id = None
        response = client.list_user_pools(MaxResults=10)
        for user_pool in response['UserPools']:
            if user_pool['Name'] == user_pool_name:
                user_pool_id = user_pool['Id']
        return user_pool_id
    except ClientError as e:
        raise e


def get_user_pool_client_id(user_pool_client_name, user_pool_id, region):

    client = boto3.client('cognito-idp')

    try:
        user_pool_client_id = None
        response = client.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=10)
        for user_pool_client in response['UserPoolClients']:
            if user_pool_client['ClientName'] == user_pool_client_name:
                user_pool_client_id = user_pool_client['ClientId']
        return user_pool_client_id
    except ClientError as e:
        raise e


def replace_string_in_file(str_list, source_file, target_file):

    with open(source_file, 'r') as source:
        replace_string = source.read()
        for i, string_couple in enumerate(str_list):
            if string_couple[1]:
                replace_string = replace_string.replace(string_couple[0], string_couple[1])
            else:
                replace_string = replace_string.replace(string_couple[0], 'NOT_FOUND')

    with open(target_file, 'w') as newfile:
        newfile.write(replace_string)
    return


def prepare_web_files(region):

    api_endpoint = get_execute_api_endpoint('MysfitsApi', region)
    # If no api endpoint then the web site cannot work
    if not api_endpoint:
        print(f'Found no API MysfitsApi')
        sys.exit(1)

    click_processing_api_endpoint = get_execute_api_endpoint('ClickProcessingApi', region)
    # If no api endpoint then there will be no click stream processing
    if not api_endpoint:
        print(f'Found no API ClickProcessingApi')

    questions_api_endpoint = get_execute_api_endpoint('QuestionsAPI', region)
    # If no api endpoint then no questions will be collected
    if not api_endpoint:
        print(f'Found no API QuestionsAPI')

    recommendations_api_endpoint = get_execute_api_endpoint('RecommendationsAPI', region)
    # If no api endpoint then no questions will be collected
    if not api_endpoint:
        print(f'Found no API RecommendationsAPI')

    user_pool_id = get_user_pool_id('MysfitsUserPool', region)
    # If no user_pool_id then login management will not be possible
    if not user_pool_id:
        print('Found no user pool MysfitsUserPool')

    user_pool_client_id = get_user_pool_client_id('MysfitsUserPoolClient', user_pool_id, region)
    # If no user_pool_client_id then login management will not be possible
    if not user_pool_client_id:
        print('Found no user pool client MysfitsUserPoolClient')

    # for index.html
    str_list = [
        ('REPLACE_ME_mysfitsApiEndpoint', api_endpoint),
        ('REPLACE_ME_streamingApiEndpoint', click_processing_api_endpoint),
        ('REPLACE_ME_questionsApiEndpoint', questions_api_endpoint),
        ('REPLACE_ME_recommendationsApiEndpoint', recommendations_api_endpoint),
        ('REPLACE_ME_REGION', region),
        ('REPLACE_ME_USER_POOL_ID', user_pool_id),
        ('REPLACE_ME_USER_POOL_CLIENT_ID', user_pool_client_id)
    ]
    replace_string_in_file(str_list, 'web/index.html', 'web/index.html')

    # for register.html
    str_list = [
        ('REPLACE_ME_USER_POOL_ID', user_pool_id),
        ('REPLACE_ME_USER_POOL_CLIENT_ID', user_pool_client_id)
    ]
    replace_string_in_file(str_list, 'web/register.html', 'web/register.html')

    # for confirm.html
    str_list = [
        ('REPLACE_ME_USER_POOL_ID', user_pool_id),
        ('REPLACE_ME_USER_POOL_CLIENT_ID', user_pool_client_id)
    ]
    replace_string_in_file(str_list, 'web/confirm.html', 'web/confirm.html')


def prepare_kinesis_file(region):

    api_endpoint = get_execute_api_endpoint('MysfitsApi', region)
    if not api_endpoint:
        print('Found no API MysfitsApi')

    # for kinesis_firehose_stack.py
    str_list = [
        ('REPLACE_ME_API_URL', api_endpoint)
    ]
    replace_string_in_file(str_list, 'webgen/kinesis_firehose_stack.py', 'webgen/kinesis_firehose_stack.py')


def prepare_xray_file(region):

    # for xray_stack.py
    str_list = [
        ('REPLACE_ME_RECEIVER_EMAIL', receiver_email)
    ]
    replace_string_in_file(str_list, 'webgen/xray_stack.py', 'webgen/xray_stack.py')


def get_sagemaker_endpoint_name(prefix, region):

    sm_client = boto3.client('sagemaker', region_name=region)
    sm_endpoint_name = None

    try:
        response = sm_client.list_endpoints(
            SortBy='CreationTime',
            SortOrder='Descending',
            NameContains=prefix,
            StatusEquals='InService'
        )
        if response['Endpoints']:
            sm_endpoint_name = response['Endpoints'][0]['EndpointName']
    except ClientError as e:
        raise e

    return sm_endpoint_name


def prepare_recommendations_file(region):

    sagemaker_endpoint_name = get_sagemaker_endpoint_name('knn-', region)
    if not sagemaker_endpoint_name:
        print(f'Found no endpoint for lambda recommendations.py')

    # for recommendations.py
    str_list = [
        ('REPLACE_ME_SAGEMAKER_ENDPOINT_NAME', sagemaker_endpoint_name)
    ]
    replace_string_in_file(str_list, 'lambda_recommendations/service/recommendations.py', 'lambda_recommendations/service/recommendations.py')


if __name__ == '__main__':
    # Get the two arguments region and update type
    api_region = os.environ['AWS_DEFAULT_REGION']
    update_type = sys.argv[1]

    if update_type == 'replace_web_endpoints_and_cognito_ids':
        prepare_web_files(api_region)
    elif update_type == 'replace_clickprocessingapi_endpoint':
        prepare_kinesis_file(api_region)
    elif update_type == 'replace_email':
        prepare_xray_file(api_region)
    elif update_type == 'replace_recommendationsapi_endpoint':
        prepare_recommendations_file(api_region)
