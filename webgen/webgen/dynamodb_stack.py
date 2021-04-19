from aws_cdk import (
    core,
    aws_dynamodb as dynamo_db,
)


class DynamoDBStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = dynamo_db.Table(self, "MysfitsTable",
                                     table_name="MysfitsTable",
                                     partition_key=dynamo_db.Attribute(name="MysfitId",
                                                                       type=dynamo_db.AttributeType.STRING),
                                     billing_mode=dynamo_db.BillingMode.PROVISIONED,  # default
                                     read_capacity=5,   # default
                                     write_capacity=5,  # default
                                     # stream=dynamo_db.StreamViewType.NEW_IMAGE
                                     )

        self.table.add_global_secondary_index(
            index_name="LawChaosIndex",
            read_capacity=5,   # default
            write_capacity=5,  # default
            partition_key=dynamo_db.Attribute(name="LawChaos", type=dynamo_db.AttributeType.STRING),
            sort_key=dynamo_db.Attribute(name="MysfitId", type=dynamo_db.AttributeType.STRING),
            projection_type=dynamo_db.ProjectionType.ALL
        )

        self.table.add_global_secondary_index(
            index_name="GoodEvilIndex",
            read_capacity=5,   # default
            write_capacity=5,  # default
            partition_key=dynamo_db.Attribute(name="GoodEvil", type=dynamo_db.AttributeType.STRING),
            sort_key=dynamo_db.Attribute(name="MysfitId", type=dynamo_db.AttributeType.STRING),
            projection_type=dynamo_db.ProjectionType.ALL
        )

        core.CfnOutput(self, "DynamodbTableName", value=self.table.table_name)
