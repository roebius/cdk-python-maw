from aws_cdk import (
    core as cdk,
    aws_cloudfront as cloudfront,
    aws_iam as _iam,
    aws_s3 as _s3,
    aws_s3_deployment as s3deploy,

)
import os


class WebApplicationStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        web_app_root = os.path.abspath('./web')

        bucket = _s3.Bucket(
            self, 'Bucket',
            website_index_document='index.html'
        )

        origin = cloudfront.OriginAccessIdentity(
            self, 'BucketOrigin',
            comment='mythical-mysfits'
        )

        bucket.grant_read(_iam.CanonicalUserPrincipal(
            origin.cloud_front_origin_access_identity_s3_canonical_user_id
        ))

        cdn = cloudfront.CloudFrontWebDistribution(
            self, 'CloudFront',
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.ALLOW_ALL,
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            origin_configs=[
                cloudfront.SourceConfiguration(
                    behaviors=[
                        cloudfront.Behavior(
                            is_default_behavior=True,
                            max_ttl=cdk.Duration.seconds(31536000),
                            allowed_methods=cloudfront.CloudFrontAllowedMethods.GET_HEAD_OPTIONS
                        )
                    ],
                    origin_path='/web',
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=bucket,
                        origin_access_identity=origin
                    )
                )
            ]
        )

        s3deploy.BucketDeployment(
            self, 'DeployWebsite',
            sources=[
                s3deploy.Source.asset(web_app_root)
            ],
            destination_key_prefix='web/',
            destination_bucket=bucket,
            distribution=cdn,
            retain_on_delete=False
        )

        cdk.CfnOutput(self, 'CloudFrontURL', description='The CloudFront distribution URL', value='https://' + cdn.domain_name)
