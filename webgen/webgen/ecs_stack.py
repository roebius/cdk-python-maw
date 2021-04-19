from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as _iam,
    aws_ecs_patterns as ecs_patterns,
    core as cdk,
)


class EcsStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc, ecr_repository, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a Fargate Cluster
        self.ecs_cluster = ecs.Cluster(
            self, 'WebEc2Cluster',
            cluster_name='MythicalMysfits-Cluster',
            vpc=vpc
        )

        self.ecs_cluster.connections.allow_from_any_ipv4(ec2.Port.tcp(8080))

        self.ecs_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, 'MythicalMysfits-FargateService',
            service_name='MythicalMysfits-FargateService',
            cluster=self.ecs_cluster,
            desired_count=1,
            public_load_balancer=True,
            min_healthy_percent=1,
            task_image_options=ecs_patterns.NetworkLoadBalancedTaskImageOptions(
                enable_logging=True,
                container_name='MythicalMysfits-Service',
                container_port=8080,
                image=ecs.ContainerImage.from_ecr_repository(ecr_repository)
            )
        )

        self.ecs_service.service.connections.allow_from(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(8080)
        )

        task_definition_policy_stm = _iam.PolicyStatement()
        task_definition_policy_stm.add_actions(
            # Rules which allow ECS to attach network interfaces to instances on your behalf in order for awsvpc networking mode to work right
            "ec2:AttachNetworkInterface",
            "ec2:CreateNetworkInterface",
            "ec2:CreateNetworkInterfacePermission",
            "ec2:DeleteNetworkInterface",
            "ec2:DeleteNetworkInterfacePermission",
            "ec2:Describe*",
            "ec2:DetachNetworkInterface",
            # Rules which allow ECS to update load balancers on your behalf with the information about how to send traffic to your containers
            "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
            "elasticloadbalancing:DeregisterTargets",
            "elasticloadbalancing:Describe*",
            "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
            "elasticloadbalancing:RegisterTargets",
            # Rules which allow ECS to run tasks that have IAM roles assigned to them.
            "iam:PassRole",
            # Rules that let ECS create and push logs to CloudWatch.
            "logs:DescribeLogStreams",
            "logs:CreateLogGroup",
        )
        task_definition_policy_stm.add_all_resources()
        self.ecs_service.service.task_definition.add_to_execution_role_policy(task_definition_policy_stm)

        task_role_policy_stm = _iam.PolicyStatement()
        task_role_policy_stm.add_actions(
            # Allow the ECS Tasks to download images from ECR
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            # Allow the ECS tasks to upload logs to CloudWatch
            "logs:CreateLogStream",
            "logs:CreateLogGroup",
            "logs:PutLogEvents",
            # Allow the ECS tasks to access the DynamoDB table to populate it upon startup.
            "dynamodb:*"
        )
        task_role_policy_stm.add_all_resources()
        self.ecs_service.service.task_definition.add_to_task_role_policy(task_role_policy_stm)

        cdk.CfnOutput(self, "WebLoadBalancerDNS", value=self.ecs_service.load_balancer.load_balancer_dns_name)

        cdk.CfnOutput(self, "WebLoadBalancerARN", value=self.ecs_service.load_balancer.load_balancer_arn)
