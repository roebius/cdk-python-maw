import boto3
from botocore.exceptions import ClientError


if __name__ == '__main__':

    try:
        sm_client = boto3.client('sagemaker')
        response = sm_client.list_endpoints(
            SortBy='CreationTime',
            SortOrder='Descending',
            NameContains='knn',
            StatusEquals='InService'
        )
        if response['Endpoints']:
            print('false')
        else:
            print('true')
    except ClientError as e:
        raise e
