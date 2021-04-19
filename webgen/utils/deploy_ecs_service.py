import boto3
from botocore.exceptions import ClientError


if __name__ == '__main__':

    ecs_client = boto3.client('ecs')
    response = ecs_client.update_service(
        cluster='MythicalMysfits-Cluster',
        service='MythicalMysfits-FargateService',
        forceNewDeployment=True,
    )
