from aws_cdk import (
    aws_ecr as ecr,
    core,
)


class EcrStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ecr_repository = ecr.Repository(
            self, 'Repository',
            repository_name='mythicalmysfits/service',

        )
