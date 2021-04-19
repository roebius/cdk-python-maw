from aws_cdk import (
    aws_ec2 as ec2,
    core,
)


class NetworkStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        # NOTE: Limit AZs to avoid reaching resource quotas
        self.vpc = ec2.Vpc(
            self, "WebVpc",
            max_azs=2,
            nat_gateways=1
        )
