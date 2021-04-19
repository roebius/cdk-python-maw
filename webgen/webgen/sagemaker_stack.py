from aws_cdk import (
    core as cdk,
    aws_apigateway as apigw,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_sagemaker as sagemaker,
)


class SageMakerStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # # Create role and policiy for the SageMaker notebook
        # mysfits_notebook_role = _iam.Role(
        #     self, 'MysfitsNotbookRole',
        #     assumed_by=_iam.ServicePrincipal('sagemaker.amazonaws.com')
        # )
        #
        # mysfits_notebook_policy_stm = _iam.PolicyStatement()
        # mysfits_notebook_policy_stm.add_actions('sagemaker:*',
        #                                         'ecr:GetAuthorizationToken',
        #                                         'ecr:GetDownloadUrlForLayer',
        #                                         'ecr:BatchGetImage',
        #                                         'ecr:BatchCheckLayerAvailability',
        #                                         'cloudwatch:PutMetricData',
        #                                         'logs:CreateLogGroup',
        #                                         'logs:CreateLogStream',
        #                                         'logs:DescribeLogStreams',
        #                                         'logs:PutLogEvents',
        #                                         'logs:GetLogEvents',
        #                                         's3:CreateBucket',
        #                                         's3:ListBucket',
        #                                         's3:GetBucketLocation',
        #                                         's3:GetObject',
        #                                         's3:PutObject',
        #                                         's3:DeleteObject')
        # mysfits_notebook_policy_stm.add_all_resources()
        #
        # mysfits_notebook_policy_passrole_stm =  _iam.PolicyStatement()
        # mysfits_notebook_policy_passrole_stm.add_actions('iam:PassRole')
        # mysfits_notebook_policy_passrole_stm.add_all_resources()
        # mysfits_notebook_policy_passrole_stm.add_condition(
        #     'StringEquals',
        #     {
        #         'iam:PassedToService': 'sagemaker.amazonaws.com',
        #     }
        # )
        #
        # _iam.Policy(
        #     self, 'MysfitsNotebookPolicy',
        #     statements=[
        #         mysfits_notebook_policy_stm,
        #         mysfits_notebook_policy_passrole_stm
        #     ],
        #     roles=[mysfits_notebook_role]
        # )
        #
        # # Create notebook
        # notebook_instance = sagemaker.CfnNotebookInstance(
        #     self, 'MythicalMysfits-SageMaker-Notebook',
        #     instance_type='ml.t2.medium',
        #     role_arn=mysfits_notebook_role.role_arn
        # )

        # Create the recommendations lambda function with its policy for use with the inference endpoint
        recommendations_lambda_function_policy_stm = _iam.PolicyStatement()
        recommendations_lambda_function_policy_stm.add_actions('sagemaker:InvokeEndpoint')
        recommendations_lambda_function_policy_stm.add_all_resources()

        mysfits_recommendations = _lambda.Function(
            self, 'RecommendationsFunction',
            handler="recommendations.recommend",
            runtime=_lambda.Runtime.PYTHON_3_6,
            description='A microservice backend to invoke a SageMaker endpoint.',
            memory_size=128,
            code=_lambda.Code.asset('./lambda_recommendations/service'),
            timeout=cdk.Duration.seconds(30),
            initial_policy=[recommendations_lambda_function_policy_stm],
            # tracing=_lambda.Tracing.ACTIVE
        )

        # Create APIGateway with policy
        recommendations_api_role = _iam.Role(
            self, 'RecommendationsApiRole',
            assumed_by=_iam.ServicePrincipal('apigateway.amazonaws.com')
        )
        api_policy = _iam.PolicyStatement()
        api_policy.add_actions("lambda:InvokeFunction")
        api_policy.add_resources(mysfits_recommendations.function_arn)
        api_policy.effect = _iam.Effect.ALLOW
        # Associate policy to role
        _iam.Policy(
            self, "RecommendationsApiPolicy",
            policy_name="recommendations_api_policy",
            statements=[api_policy],
            roles=[recommendations_api_role]
        )

        api = apigw.LambdaRestApi(
            self, 'APIEndpoint',
            handler=mysfits_recommendations,
            options=apigw.LambdaRestApiProps(
                rest_api_name='RecommendationsAPI',
                deploy_options=apigw.StageOptions(
                    tracing_enabled=True
                ),
                handler=mysfits_recommendations
            ),
            proxy=False
        )

        # Create methods
        recommendations_integration = apigw.LambdaIntegration(
            mysfits_recommendations,
            credentials_role=recommendations_api_role,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code='200',
                    response_templates={"application/json": '{"status":"OK"}'},
                    # response_parameters={
                    #     "method.response.header.Access-Control-Allow-Headers": "'Content-Type'",
                    #     "method.response.header.Access-Control-Allow-Methods": "'OPTIONS,POST'",
                    #     "method.response.header.Access-Control-Allow-Origin": "'*'"
                    # }
                )
            ],
        )

        recommendations_method = api.root.add_resource('recommendations')
        recommendations_method.add_method(
            'POST',
            recommendations_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Headers': True,
                        'method.response.header.Access-Control-Allow-Methods': True,
                        'method.response.header.Access-Control-Allow-Origin': True,
                    }
                )
            ],
            authorization_type=apigw.AuthorizationType.NONE
        )

        recommendations_method.add_method(
            'OPTIONS',
            integration=apigw.MockIntegration(
                integration_responses=[apigw.IntegrationResponse(
                    status_code='200',
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Credentials': "'false'",
                        'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,GET,PUT,POST,DELETE'",
                    }
                )
                ],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[apigw.MethodResponse(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Credentials': True,
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )
            ]
        )
