from aws_cdk import (
    aws_apigateway as apigw,
    aws_elasticloadbalancingv2 as elbv2,
    core,
)
import json


def generate_swagger_spec_json(account, region, dns_name, user_pool_id, vpc_link: apigw.VpcLink):
    # The APIGateway API's are defined in a Swagger file that will be used to generate the API during the stack creation
    with open('utils/templates/api-swagger.json', 'r') as swagger_file:
        file_source = swagger_file.read()
        replace_string = file_source.replace('REPLACE_ME_REGION', region)
        replace_string = replace_string.replace('REPLACE_ME_ACCOUNT_ID', account)
        replace_string = replace_string.replace('REPLACE_ME_COGNITO_USER_POOL_ID', user_pool_id)
        replace_string = replace_string.replace('REPLACE_ME_VPC_LINK_ID', vpc_link.vpc_link_id)
        replace_string = replace_string.replace('REPLACE_ME_NLB_DNS', dns_name)
        spec_json = json.loads(replace_string)
        return spec_json


class APIGatewayStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str,
                 load_balancer_dns_name,
                 load_balancer_arn,
                 user_pool_id,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        nlb = elbv2.NetworkLoadBalancer.from_network_load_balancer_attributes(
            self, 'NLB',
            load_balancer_arn=load_balancer_arn
        )

        vpc_link = apigw.VpcLink(self, 'VPCLink',
                                 description='VPCLink for our  REST API',
                                 vpc_link_name='MysfitsApiVpcLink',
                                 targets=[nlb]
                                 )

        json_schema = generate_swagger_spec_json(self.account, self.region,
                                                 load_balancer_dns_name,
                                                 user_pool_id,
                                                 vpc_link)

        api = apigw.CfnRestApi(
            self, 'Schema',
            name='MysfitsApi',
            body=json_schema,
            endpoint_configuration=apigw.CfnRestApi.EndpointConfigurationProperty(types=['REGIONAL']),  # types: EDGE, REGIONAL, PRIVATE
            fail_on_warnings=True
        )

        prod = apigw.CfnDeployment(
            self, 'Prod',
            rest_api_id=api.ref,
            stage_name='prod'
        )

        core.CfnOutput(self, "APIID", description='API Gateway ID', value=api.ref)
