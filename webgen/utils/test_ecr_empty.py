import boto3
from botocore.exceptions import ClientError


if __name__ == '__main__':

    try:
        ecr_client = boto3.client('ecr')
        response = ecr_client.list_images(
            repositoryName='mythicalmysfits/service',
            filter={'tagStatus': 'ANY'}
        )
        if response['imageIds']:
            print('false')
        else:
            print('true')
    except ClientError as e:
        if e.response['Error']['Code'] != 'RepositoryNotFoundException':
            raise e
        else:
            print('true')
