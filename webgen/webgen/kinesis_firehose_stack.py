from aws_cdk import (
    core as cdk,
    aws_dynamodb as dynamo_db,
    aws_apigateway as apigw,
    aws_iam as _iam,
    aws_kinesisfirehose as kinfire,
    aws_lambda as _lambda,
    aws_s3 as _s3,
)


mysfits_api_url = 'REPLACE_ME_API_URL'


class KinesisFirehoseStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, table: dynamo_db.Table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Bucket for the processed stream events
        # --------------------------------------
        clicks_destination_bucket = _s3.Bucket(
            self, 'Bucket',
            versioned=False  # True
        )

        # Lambda function for processing the stream
        # -----------------------------------------
        # Policy statement for accessing the DynamoDB table
        lambda_function_policy_stm = _iam.PolicyStatement()
        lambda_function_policy_stm.add_actions('dynamodb:GetItem')
        lambda_function_policy_stm.add_resources(table.table_arn)

        # Lambda processor function
        mysfits_click_processor = _lambda.Function(
            self, 'Function',
            handler="streamProcessor.processRecord",
            runtime=_lambda.Runtime.PYTHON_3_6,
            description='An Amazon Kinesis Firehose stream processor that enriches click records to not just '
                        'include a mysfitId, but also other attributes that can be analyzed later.',
            memory_size=128,
            code=_lambda.Code.asset('./lambda_streaming_processor'),
            timeout=cdk.Duration.seconds(60),
            initial_policy=[lambda_function_policy_stm],
            environment={
                'MYSFITS_API_URL': mysfits_api_url
            }
        )

        # Firehose delivery stream
        # ------------------------
        # Initialize role
        firehose_delivery_role = _iam.Role(
            self, "FirehoseDeliveryRole",
            role_name='FirehoseDeliveryRole',
            assumed_by=_iam.ServicePrincipal('firehose.amazonaws.com'),
        )
        # Statement with access to S3 bucket
        firehose_delivery_policy_s3_stm = _iam.PolicyStatement()
        firehose_delivery_policy_s3_stm.add_actions("s3:AbortMultipartUpload",
                                                    "s3:GetBucketLocation",
                                                    "s3:GetObject",
                                                    "s3:ListBucket",
                                                    "s3:ListBucketMultipartUploads",
                                                    "s3:PutObject")
        firehose_delivery_policy_s3_stm.add_resources(clicks_destination_bucket.bucket_arn)
        firehose_delivery_policy_s3_stm.add_resources(clicks_destination_bucket.arn_for_objects('*'))
        firehose_delivery_policy_s3_stm.effect = _iam.Effect.ALLOW
        # Statement with access to Lambda function
        firehose_delivery_policy_lambda_stm = _iam.PolicyStatement()
        firehose_delivery_policy_lambda_stm.add_actions("lambda:InvokeFunction")
        firehose_delivery_policy_lambda_stm.add_actions("lambda:GetFunctionConfiguration")
        firehose_delivery_policy_lambda_stm.add_resources(mysfits_click_processor.function_arn)
        firehose_delivery_policy_lambda_stm.effect = _iam.Effect.ALLOW
        # Add policies to role
        firehose_delivery_role.add_to_policy(firehose_delivery_policy_s3_stm)
        firehose_delivery_role.add_to_policy(firehose_delivery_policy_lambda_stm)
        # Create delivery stream
        mysfits_firehose_to_s3 = kinfire.CfnDeliveryStream(
            self, "DeliveryStream",
            delivery_stream_name="DeliveryStream",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=kinfire.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=clicks_destination_bucket.bucket_arn,
                buffering_hints=kinfire.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=1
                ),
                compression_format="UNCOMPRESSED",
                error_output_prefix="errors/",
                prefix="firehose/",
                processing_configuration=kinfire.CfnDeliveryStream.ProcessingConfigurationProperty(
                    enabled=True,
                    processors=[kinfire.CfnDeliveryStream.ProcessorProperty(
                        type="Lambda",
                        parameters=[kinfire.CfnDeliveryStream.ProcessorParameterProperty(
                            parameter_name="LambdaArn",
                            parameter_value=mysfits_click_processor.function_arn
                        )]
                    )
                    ]
                ),
                role_arn=firehose_delivery_role.role_arn,
            )
        )

        # API Gateway as proxy to the Firehose stream
        # -------------------------------------------
        # Initialize role
        click_processing_api_role = _iam.Role(
            self, "ClickProcessingApiRole",
            role_name="ClickProcessingApiRole",
            assumed_by=_iam.ServicePrincipal("apigateway.amazonaws.com"))

        api_policy = _iam.PolicyStatement()
        api_policy.add_actions("firehose:PutRecord")
        api_policy.add_resources(mysfits_firehose_to_s3.attr_arn)
        api_policy.effect = _iam.Effect.ALLOW
        # Associate policy to role
        _iam.Policy(
            self, "ClickProcessingApiPolicy",
            policy_name="api_gateway_firehose_proxy_role",
            statements=[api_policy],
            roles=[click_processing_api_role]
        )
        # Create API gateway
        api = apigw.RestApi(
            self, "APIEndpoint",
            rest_api_name="ClickProcessingApi",
            endpoint_types=[apigw.EndpointType.REGIONAL]
        )
        # Add the resource endpoint and the method used to send clicks to Firehose
        clicks = api.root.add_resource('clicks')
        clicks.add_method(
            'PUT',
            integration=apigw.AwsIntegration(
                service='firehose',
                integration_http_method='POST',
                action='PutRecord',
                options=apigw.IntegrationOptions(
                    connection_type=apigw.ConnectionType.INTERNET,
                    credentials_role=click_processing_api_role,
                    integration_responses=[apigw.IntegrationResponse(
                        status_code='200',
                        response_templates={
                            "application/json": '{"status":"OK"}'
                        },
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Headers": "'Content-Type'",
                            "method.response.header.Access-Control-Allow-Methods": "'OPTIONS,PUT'",
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    )
                    ],
                    request_parameters={
                        "integration.request.header.Content-Type": "'application/x-amz-json-1.1'"
                    },
                    request_templates={
                        "application/json": "{ \"DeliveryStreamName\": \"" + mysfits_firehose_to_s3.ref + "\", \"Record\": {   \"Data\": \"$util.base64Encode($input.json('$'))\" } }"
                    },
                )
            ),
            method_responses=[apigw.MethodResponse(
                status_code='200',
                response_parameters={
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Methods": True,
                    "method.response.header.Access-Control-Allow-Origin": True
                }
            )
            ]
        )

        clicks.add_method(
            'OPTIONS',
            integration=apigw.MockIntegration(
                integration_responses=[apigw.IntegrationResponse(
                    status_code='200',
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Headers":
                            "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'",
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Credentials":
                            "'false'",
                        "method.response.header.Access-Control-Allow-Methods":
                            "'OPTIONS,GET,PUT,POST,DELETE'"
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
