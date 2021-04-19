from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as _iam,
    aws_ecs_patterns as ecs_patterns,
    core,
)


class NetworkECRStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        # NOTE: Limit AZs to avoid reaching resource quotas
        vpc = ec2.Vpc(
            self, "WebVpc",
            max_azs=2,
            nat_gateways=1
        )

        # # FOR INCREASED SECURITY
        # # Create a VPC endpoint for DynamoDB and associate a policy
        # dynamodb_endpoint = vpc.add_gateway_endpoint(
        #     'DynamoDbEndpoint',
        #     service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        #     subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE)]
        # )
        #
        # dynamodb_policy = _iam.PolicyStatement()
        # dynamodb_policy.add_any_principal()
        # dynamodb_policy.add_actions('*')
        # dynamodb_policy.add_all_resources()
        # dynamodb_endpoint.add_to_policy(dynamodb_policy)

        ecs_task_inline_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllActionsOnTable",
                    "Action": [
                        "dynamodb:*",
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:dynamodb:" + self.region + ":" + self.account + ":table/MysfitsTable",
                        "arn:aws:dynamodb:" + self.region + ":" + self.account + ":table/MysfitsTable/index/*"
                    ]
                }
            ]
        }

        # Create a Fargate Cluster
        cluster = ecs.Cluster(
            self, 'WebEc2Cluster',
            vpc=vpc
        )

        ecs_access_role = _iam.Role.from_role_arn(scope=self, id="ECSAccessRole",
                                                  role_arn="arn:aws:iam::" + self.account + ":role/ecsTaskExecutionRole",
                                                  mutable=False
                                                  )

        ecs_task_role = _iam.Role.from_role_arn(scope=self, id="ECSTaskRole",
                                                role_arn="arn:aws:iam::" + self.account + ":role/ecsTaskExecutionRole",
                                                mutable=True
                                                )

        # # A way to add the policy
        # ecs_task_role.add_to_policy(_iam.PolicyStatement(
        #     actions=["dynamodb:*"],
        #     resources=["arn:aws:dynamodb:" + self.region + ":" + self.account + ":table/MysfitsTable"],
        #     effect=_iam.Effect.ALLOW
        # ))

        # Alternative way to add the policy
        ecs_task_inline_policy_document = _iam.PolicyDocument.from_json(ecs_task_inline_policy)
        ecs_task_policy = _iam.Policy(self, "ECSTaskPolicy", document=ecs_task_inline_policy_document)
        ecs_task_role.attach_inline_policy(ecs_task_policy)

        task_image_options = ecs_patterns.NetworkLoadBalancedTaskImageOptions(
            image=ecs.ContainerImage.from_registry(self.account +
                                                   ".dkr.ecr." + self.region + ".amazonaws.com/mythicalmysfits/webservice"),
            container_port=8080,
            execution_role=ecs_access_role,
            enable_logging=True,
            task_role=ecs_task_role
        )

        self.fargate_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, "MythicalMysfits-Service",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            public_load_balancer=True,
            task_image_options=task_image_options
        )

        self.fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8080),
            description="Allow http inbound from VPC"
        )

        core.CfnOutput(self, "WebLoadBalancerDNS", value=self.fargate_service.load_balancer.load_balancer_dns_name)
        # self.lb_dns_name = core.CfnOutput(
        #     self, "WebLoadBalancerDNS",
        #     value=self.fargate_service.load_balancer.load_balancer_dns_name,
        #     export_name="lb-dns-name"
        # ).import_value

        core.CfnOutput(self, "WebLoadBalancerARN", value=self.fargate_service.load_balancer.load_balancer_arn)
        # self.lb_dns_arn = core.CfnOutput(
        #     self, "WebLoadBalancerARN",
        #     value=self.fargate_service.load_balancer.load_balancer_arn,
        #     export_name="lb-dns-arn"
        # ).import_value
