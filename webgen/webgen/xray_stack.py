from aws_cdk import (
    core as cdk,
    aws_iam as _iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_lambda as _lambda,
    aws_lambda_event_sources as event,
    aws_dynamodb as dynamo_db,
    aws_apigateway as apigw,
)

receiver_email = 'REPLACE_ME_RECEIVER_EMAIL'


class XRayStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamo_db.Table(self, "MysfitsQuestionsTable",
                                table_name="MysfitsQuestionsTable",
                                partition_key=dynamo_db.Attribute(name="QuestionId",
                                                                  type=dynamo_db.AttributeType.STRING),
                                stream=dynamo_db.StreamViewType.NEW_IMAGE
                                )

        post_question_lambda_function_policy_stm_ddb =  _iam.PolicyStatement()
        post_question_lambda_function_policy_stm_ddb.add_actions("dynamodb:PutItem")
        post_question_lambda_function_policy_stm_ddb.add_resources(table.table_arn)

        lambda_function_policy_stm_xray = _iam.PolicyStatement()
        lambda_function_policy_stm_xray.add_actions("xray:PutTraceSegments",
                                                    "xray:PutTelemetryRecords",
                                                    "xray:GetSamplingRules",
                                                    "xray:GetSamplingTargets",
                                                    "xray:GetSamplingStatisticSummaries")
        lambda_function_policy_stm_xray.add_all_resources()

        # Lambda processor function
        mysfits_post_question = _lambda.Function(
            self, 'PostQuestionFunction',
            handler="mysfitsPostQuestion.postQuestion",
            runtime=_lambda.Runtime.PYTHON_3_6,
            description='A microservice Lambda function that receives a new question submitted to the MythicalMysfits'
                        ' website from a user and inserts it into a DynamoDB database table.',
            memory_size=128,
            code=_lambda.Code.asset('./lambda_questions/PostQuestionsService'),
            timeout=cdk.Duration.seconds(30),
            initial_policy=[post_question_lambda_function_policy_stm_ddb,
                            lambda_function_policy_stm_xray],
            tracing=_lambda.Tracing.ACTIVE
        )

        topic = sns.Topic(
            self, 'Topic',
            display_name='MythicalMysfitsQuestionsTopic',
            topic_name='MythicalMysfitsQuestionsTopic'
        )
        topic.add_subscription(subs.EmailSubscription(receiver_email))

        post_question_lambda_function_policy_stm_sns =  _iam.PolicyStatement()
        post_question_lambda_function_policy_stm_sns.add_actions("sns:Publish")
        post_question_lambda_function_policy_stm_sns.add_resources(topic.topic_arn)

        mysfits_process_questions_stream = _lambda.Function(
            self, 'ProcessQuestionStreamFunction',
            handler="mysfitsProcessStream.processStream",
            runtime=_lambda.Runtime.PYTHON_3_6,
            description='An AWS Lambda function that will process all new questions posted to mythical mysfits'
                        ' and notify the site administrator of the question that was asked.',
            memory_size=128,
            code=_lambda.Code.asset('./lambda_questions/ProcessQuestionsStream'),
            timeout=cdk.Duration.seconds(30),
            initial_policy=[post_question_lambda_function_policy_stm_sns,
                            lambda_function_policy_stm_xray],
            environment={
                'SNS_TOPIC_ARN': topic.topic_arn
            },
            tracing=_lambda.Tracing.ACTIVE,
            events=[
                event.DynamoEventSource(
                    table,
                    starting_position=_lambda.StartingPosition.TRIM_HORIZON,
                    batch_size=1
                )
            ]
        )

        questions_api_role = _iam.Role(
            self, 'QuestionsApiRole',
            assumed_by=_iam.ServicePrincipal('apigateway.amazonaws.com')
        )
        api_policy = _iam.PolicyStatement()
        api_policy.add_actions("lambda:InvokeFunction")
        api_policy.add_resources(mysfits_post_question.function_arn)
        api_policy.effect = _iam.Effect.ALLOW
        # Associate policy to role
        _iam.Policy(
            self, "QuestionsApiPolicy",
            policy_name="questions_api_policy",
            statements=[api_policy],
            roles=[questions_api_role]
        )

        # Create API gateway
        questions_integration = apigw.LambdaIntegration(
            mysfits_post_question,
            credentials_role=questions_api_role,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code='200',
                    response_templates={"application/json": '{"status":"OK"}'}
                )
            ],
        )

        api = apigw.LambdaRestApi(
            self, 'APIEndpoint',
            handler=mysfits_post_question,
            options=apigw.LambdaRestApiProps(
                rest_api_name='QuestionsAPI',
                deploy_options=apigw.StageOptions(
                    tracing_enabled=True
                ),
                handler=mysfits_post_question
            ),
            proxy=False
        )

        questions_method = api.root.add_resource('questions')
        questions_method.add_method(
            'POST', questions_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code='200'
                )
            ],
            authorization_type=apigw.AuthorizationType.NONE
        )

        questions_method.add_method(
            'OPTIONS',
            integration=apigw.MockIntegration(
                integration_responses=[apigw.IntegrationResponse(
                    status_code='200',
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Credentials': "'false'",
                        'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,GET,PUT,POST,DELETE'"
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
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Methods": True,
                    "method.response.header.Access-Control-Allow-Credentials": True,
                    "method.response.header.Access-Control-Allow-Origin": True
                }
            )
            ]
        )
