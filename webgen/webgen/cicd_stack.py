from aws_cdk import (
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_iam as _iam,
    aws_ecr as ecr,
    aws_ecs as ecs,
    core as cdk,
)


class CiCdStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,
                 ecr_repository: ecr.Repository,
                 ecs_service: ecs.FargateService,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        backend_repository = codecommit.Repository(
            self, 'BackendRepository',
            repository_name='MythicalMysfits-BackendRepository'
        )

        codebuild_project = codebuild.PipelineProject(
            self, 'BuildProject',
            project_name='MythicalMysfitsServiceCodeBuildProject',
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.UBUNTU_14_04_PYTHON_3_5_2,
                compute_type=codebuild.ComputeType.SMALL,
                environment_variables={
                    'AWS_ACCOUNT_ID': codebuild.BuildEnvironmentVariable(
                        type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                        value=self.account),
                    'AWS_DEFAULT_REGION': codebuild.BuildEnvironmentVariable(
                        type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                        value=self.region),
                },
                privileged=True
            )
        )

        codebuild_policy_stm = _iam.PolicyStatement()
        codebuild_policy_stm.add_resources(backend_repository.repository_arn)
        codebuild_policy_stm.add_actions(
            "codecommit:ListBranches",
            "codecommit:ListRepositories",
            "codecommit:BatchGetRepositories",
            "codecommit:GitPull"
        )
        codebuild_project.add_to_role_policy(codebuild_policy_stm)

        ecr_repository.grant_pull_push(codebuild_project.grant_principal)

        source_output = codepipeline.Artifact()
        source_action = actions.CodeCommitSourceAction(
            action_name='CodeCommit-Source',
            branch='main',
            trigger=actions.CodeCommitTrigger.EVENTS,
            repository=backend_repository,
            output=source_output
        )

        build_output = codepipeline.Artifact()
        build_action = actions.CodeBuildAction(
            action_name='Build',
            input=source_output,
            outputs=[
                build_output
            ],
            project=codebuild_project
        )

        deploy_action = actions.EcsDeployAction(
            action_name='DeployAction',
            service=ecs_service,
            input=build_output
        )

        pipeline = codepipeline.Pipeline(
            self, 'Pipeline',
            pipeline_name='MythicalMysfitsPipeline',
        )
        pipeline.add_stage(stage_name='Source', actions=[source_action])
        pipeline.add_stage(stage_name='Build', actions=[build_action])
        # # the following pipeline.add_stage doesn't work
        # pipeline.add_stage(stage_name='Deploy', actions=[deploy_action])

        cdk.CfnOutput(self, 'BackendRepositoryCloneUrlHttp',
                      description='Backend Repository CloneUrl HTTP',
                      value=backend_repository.repository_clone_url_http)

        cdk.CfnOutput(self, 'BackendRepositoryCloneUrlSsh',
                      description='Backend Repository CloneUrl SSH',
                      value=backend_repository.repository_clone_url_ssh)
