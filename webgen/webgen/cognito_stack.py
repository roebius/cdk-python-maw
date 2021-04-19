from aws_cdk import (
    aws_cognito as cognito,
    core,
)


class CognitoStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(self, 'UserPool',
                                          auto_verify=cognito.AutoVerifiedAttrs(
                                            email=True
                                          ),
                                          self_sign_up_enabled=True,
                                          user_pool_name='MysfitsUserPool'
                                          )

        user_pool_client = cognito.UserPoolClient(self, 'UserPoolClient',
                                                  user_pool=self.user_pool,
                                                  user_pool_client_name='MysfitsUserPoolClient'
                                                  )

        core.CfnOutput(self, 'CognitoUserPool',
                       description='The Cognito User Pool',
                       value=self.user_pool.user_pool_id)
        # self.user_pool_id = core.CfnOutput(
        #     self, "CognitoUserPool",
        #     description='The Cognito User Pool',
        #     value=user_pool.user_pool_id,
        #     export_name="user-pool-id"
        # ).import_value

        core.CfnOutput(self, 'CognitoUserPoolClient',
                       description='The Cognito User Pool Client',
                       value=user_pool_client.user_pool_client_id)
        # self.user_pool_client_id = core.CfnOutput(
        #     self, "CognitoUserPoolClient",
        #     description='The Cognito User Pool Client',
        #     value=user_pool_client.user_pool_client_id,
        #     export_name="user-pool-client-id"
        # ).import_value

