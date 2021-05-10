import boto3
from botocore.exceptions import ClientError
from prepare_files import get_user_pool_id, get_user_pool_client_id

# WARNING!
# This script deletes resources whose names/prefixes are included in Python lists that are passed to deletion functions.
# BEFORE LAUNCHING THE SCRIPT DOUBLE CHECK THAT IT WILL NOR DELETE ANY RESOURCES THAT DO NOT WANT TO DELETE!
# CHECK ALSO THAT THE REGION assigned to 'deployment_region_list' is the one for the resources that you want to delete.
# The lists are in the '__main__' section of the script.


def delete_buckets_by_prefix(s3_client, prefix, region):
    deleted_buckets = []
    for bucket in s3_client.list_buckets()["Buckets"]:
        bucket_name = bucket["Name"]
        # print(f'Bucket name: {bucket_name}')
        if s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint'] != region:
            # print(f'Bucket {bucket_name} is not in region {region}: ignoring')
            continue
        if prefix:
            if bucket_name[:len(prefix)] != prefix:
                # print(f'Bucket {bucket_name} has not "{prefix}" prefix: ignoring')
                continue
        s3_resource = boto3.resource('s3', region_name=region)
        bucket = s3_resource.Bucket(bucket_name)
        # for obj in bucket.objects.all():
        #     print(f'\t- {obj.key}')
        bucket.objects.delete()
        print(f'Deleted all objects in bucket bucket {bucket_name}')
        response = s3_client.delete_bucket(Bucket=bucket_name)
        deleted_buckets.append(bucket_name)

    if deleted_buckets:
        deleted_bucket_list = "\n".join(deleted_buckets)
        print(f'Deleted buckets: {deleted_bucket_list}')
    else:
        print(f'No buckets with prefix:\n{prefix}')


def clean_buckets_by_prefixes(prefixes, deployment_regions):
    print('\n---------- BUCKETS --------------------------------------------------')

    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        s3_client = boto3.client('s3', region_name=current_region)
        for prefix in prefixes:
            delete_buckets_by_prefix(s3_client, prefix, current_region)


def delete_log_groups_by_prefixes(client, prefixes):
    log_groups = client.describe_log_groups()

    for log_group in log_groups['logGroups']:
        log_group_name = log_group['logGroupName']
        for prefix in prefixes:
            if prefix.lower() in log_group_name.lower():
                response = client.delete_log_group(logGroupName=log_group_name)
                print(f"Deleted log group: {log_group_name}")


def clean_logs_by_prefixes(prefixes, deployment_regions):
    print('\n---------- LOG GROUPS -----------------------------------------------')
    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        logs_client = boto3.client('logs', region_name=current_region)
        delete_log_groups_by_prefixes(logs_client, prefixes)


def clean_tables_by_names(names, deployment_regions):
    print('\n---------- DynamoDB Tables --------------------------------------------------')

    deleted_tables = []

    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        ddb_client = boto3.client('dynamodb', region_name=current_region)
        for table_name in names:
            try:
                response = ddb_client.delete_table(
                    TableName=table_name
                )
                deleted_tables.append(table_name)
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise e

    if deleted_tables:
        deleted_table_list = "\n".join(deleted_tables)
        print(f'Deleted tables: {deleted_table_list}')
    else:
        print(f'No tables with names:\n{names}')


def clean_pools_by_names(names, deployment_regions):
    print('\n---------- Cognito User Pools --------------------------------------------------')

    deleted_pools = []

    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        cidp_client = boto3.client('cognito-idp', region_name=current_region)
        for pool_name in names:
            user_pool_id = get_user_pool_id('MysfitsUserPool', current_region)
            if user_pool_id is not None:
                try:
                    response = cidp_client.delete_user_pool(
                        UserPoolId=user_pool_id
                    )
                    deleted_pools.append(pool_name)
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        raise e

    if deleted_pools:
        deleted_pool_list = "\n".join(deleted_pools)
        print(f'Deleted pools: {deleted_pool_list}')
    else:
        print(f'No pools with names:\n{names}')


def clean_repositories_by_names(names, deployment_regions):
    print('\n---------- ECR Repositories --------------------------------------------------')

    deleted_repositories = []

    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        ecr_client = boto3.client('ecr', region_name=current_region)
        for repository_name in names:
            try:
                response = ecr_client.delete_repository(
                    repositoryName=repository_name,
                    force=True
                )
                deleted_repositories.append(repository_name)
            except ClientError as e:
                if e.response['Error']['Code'] != 'RepositoryNotFoundException':
                    raise e

    if deleted_repositories:
        deleted_repository_list = "\n".join(deleted_repositories)
        print(f'Deleted repositories: {deleted_repository_list}')
    else:
        print(f'No repositories with names:\n{names}')


def list_nat_gateways(deployment_regions):
    print('\n---------- NAT Gateways --------------------------------------------------')

    nat_gateways = []

    for current_region in deployment_regions:
        print(f'\nRegion {current_region}:')
        ec2_client = boto3.client('ec2', region_name=current_region)
        response = ec2_client.describe_nat_gateways(
            DryRun=False,
            Filters=[
                {
                    'Name': 'state',
                    'Values': [
                        'pending',
                        'failed',
                        'available',
                        'deleting',
                        'deleted'
                    ]
                },
            ],
            # MaxResults=10,
        )
        for i, gateway in enumerate(response['NatGateways']):
            nat_gateways.append((response['NatGateways'][i]['NatGatewayId'], response['NatGateways'][i]['State']))
    return nat_gateways


def clean_sagemaker_endpoints_by_prefix(deployment_regions, endpoint_prefix=None, endpoint_config_prefix=None, model_prefix=None):
    print('\n---------- Sagemaker --------------------------------------------------')

    for current_region in deployment_regions:
        sm_client = boto3.client('sagemaker', region_name=current_region)
        if endpoint_prefix:
            try:
                response = sm_client.list_endpoints(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    NameContains=endpoint_prefix,
                    StatusEquals='InService'
                )
                for endpoint in response['Endpoints']:
                    response = sm_client.delete_endpoint(
                        EndpointName=endpoint['EndpointName']
                    )
                    print(f"Deleted endpoint {endpoint['EndpointName']} in region {current_region}")
            except ClientError as e:
                raise e

        if endpoint_config_prefix:
            try:
                response = sm_client.list_endpoint_configs(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    NameContains=endpoint_config_prefix,
                )
                for endpoint_config in response['EndpointConfigs']:
                    response = sm_client.delete_endpoint_config(
                        EndpointConfigName=endpoint_config['EndpointConfigName']
                    )
                    print(f"Deleted endpoint configuration {endpoint_config['EndpointConfigName']} in region {current_region}")
            except ClientError as e:
                raise e

        if model_prefix:
            try:
                response = sm_client.list_models(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    NameContains=model_prefix,
                )
                for model in response['Models']:
                    response = sm_client.delete_model(
                        ModelName=model['ModelName']
                    )
                    print(f"Deleted model {model['ModelName']} in region {current_region}")
            except ClientError as e:
                raise e


if __name__ == '__main__':
    # WARNING!
    # This script deletes resources whose names/prefixes are included in the Python lists that you can find below.
    # BEFORE LAUNCHING THE SCRIPT DOUBLE CHECK THAT IT WILL NOR DELETE ANY RESOURCES THAT DO NOT WANT TO DELETE!
    # CHECK ALSO THAT THE REGION assigned to 'deployment_region_list' is the desired one.

    deployment_region_list = ['eu-west-1']

    # Buckets
    prefixes = [
        'mythicalmysfits',
        'sagemaker',
    ]
    clean_buckets_by_prefixes(prefixes, deployment_region_list)

    # Logs
    prefixes = [
        'mysfits',
        'welcome',
        'NotebookInstances',
        'ProcessingJobs',
        'TrainingJobs',
    ]
    clean_logs_by_prefixes(prefixes, deployment_region_list)

    # DynamoDB Tables
    names = [
        'MysfitsTable',
        'MysfitsQuestionsTable'
    ]
    clean_tables_by_names(names, deployment_region_list)

    # Cognito User Pools
    names = [
        'MysfitsUserPool',
    ]
    clean_pools_by_names(names, deployment_region_list)

    # ECR Repositories
    names = [
        'mythicalmysfits/service',
    ]
    clean_repositories_by_names(names, deployment_region_list)

    clean_sagemaker_endpoints_by_prefix(deployment_region_list,
                                        endpoint_prefix='mysfits',
                                        endpoint_config_prefix='mysfits',
                                        model_prefix='knn')

    # Check existence of any UNWANTED NAT Gateways
    current_nat_gateways = list_nat_gateways(deployment_region_list)
    if current_nat_gateways:
        for gateway in current_nat_gateways:
            print(f'Please check if the following NAT Gateway requires manual deletion: {gateway[0]}  -  state: {gateway[1]}')
    else:
        print('Found no NAT Gateway')
