from aws_cdk import core
from spa_deploy import SPADeploy


class WebgenStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # from https://github.com/nideveloper/CDK-SPA-Deploy, choose one of the two deployment options

        # Deploy using basic deployment
        SPADeploy(self, 'spaDeploy').create_basic_site(
            index_doc='index.html',
            website_folder='./web'
        )

        # # Alternative deployment, using CloudFront
        # SPADeploy(self, 'cfDeploy').create_site_with_cloudfront(
        #     index_doc='index.html',
        #     website_folder='./web'
        # )
