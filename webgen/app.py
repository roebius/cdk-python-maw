#!/usr/bin/env python3

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
# from aws_cdk import core

from webgen.webgen_stack import WebgenStack
from webgen.web_application_stack import WebApplicationStack
from webgen.network_stack import NetworkStack
from webgen.ecr_stack import EcrStack
from webgen.ecs_stack import EcsStack
from webgen.cicd_stack import CiCdStack
from webgen.network_ecr_stack import NetworkECRStack
from webgen.dynamodb_stack import DynamoDBStack
from webgen.cognito_stack import CognitoStack
from webgen.apigateway_stack import APIGatewayStack
from webgen.kinesis_firehose_stack import KinesisFirehoseStack
from webgen.sagemaker_stack import SageMakerStack
from webgen.xray_stack import XRayStack

import os

deploy_region = os.environ['AWS_DEFAULT_REGION']

app = cdk.App()

# Deploy the DynamoDB table (before the ECS service, which populates the table)
table_stack = DynamoDBStack(app, "MythicalMysfits-DynamoDB-stack",
                            env=cdk.Environment(region=deploy_region))

# Deploy the network and the ECS service
network_stack = NetworkStack(app, "MythicalMysfits-Network-stack",
                             env=cdk.Environment(region=deploy_region))

ecr_stack = EcrStack(app, "MythicalMysfits-ECR-stack",
                     env=cdk.Environment(region=deploy_region))

ecs_stack = EcsStack(app, "MythicalMysfits-ECS-stack",
                     vpc=network_stack.vpc,
                     ecr_repository=ecr_stack.ecr_repository,
                     env=cdk.Environment(region=deploy_region))
# # OPTIONAL: force this dependency if the deployment order requires it, since the Fargate service populates the DynamoDB table
# ecs_stack.add_dependency(table_stack)

# # Not used
# Deploy the CI/CD stack
# cicd_stack = CiCdStack(app, "MythicalMysfits-CICD-stack",
#                        ecr_repository=ecr_stack.ecr_repository,
#                        ecs_service=ecs_stack.ecs_service,
#                        env=cdk.Environment(region=deploy_region))

# Deploy the Cognito resourcesa
cognito_stack = CognitoStack(app, "MythicalMysfits-Cognito-stack",
                             env=cdk.Environment(region=deploy_region))

# Deploy the API Gateway for the website
apigateway_stack = APIGatewayStack(app, "MythicalMysfits-APIGateway-stack",
                                   env=cdk.Environment(region=deploy_region),
                                   load_balancer_dns_name=ecs_stack.ecs_service.load_balancer.load_balancer_dns_name,
                                   load_balancer_arn=ecs_stack.ecs_service.load_balancer.load_balancer_arn,
                                   user_pool_id=cognito_stack.user_pool.user_pool_id)

# Deploy the click processing stack
firehose_stack = KinesisFirehoseStack(app, "MythicalMysfits-KinesisFirehose-stack",
                                      env=cdk.Environment(region=deploy_region),
                                      table=table_stack.table)

# Deploy the X-Ray stack
xray_stack = XRayStack(app, "MythicalMysfits-XRay-stack",
                       env=cdk.Environment(region=deploy_region))

# Deploy the Sagemaker stack
sagemaker_stack = SageMakerStack(app, "MythicalMysfits-SageMaker-stack",
                                 env=cdk.Environment(region=deploy_region))

# Deploy the website stack based on original module-1
web_s3_stack = WebApplicationStack(app, "MythicalMysfits-Website-stack",
                                   env=cdk.Environment(region=deploy_region))

# # Deploy the website stack based on CDK-SPA-Deploy https://github.com/nideveloper/CDK-SPA-Deploy
# web_s3_stack = WebgenStack(app, "MythicalMysfits-Website-stack",
#                            env=cdk.Environment(region=deploy_region))

app.synth()
