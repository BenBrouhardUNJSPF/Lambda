import boto3
from botocore.exceptions import BotoCoreError, ClientError

class DynamoDBClient:
    """
    A client for interacting with a DynamoDB table.

    This client supports both same-account and cross-account queries. For cross-account queries, it uses STS to assume a role.

    Attributes:
        table_name (str): The name of the DynamoDB table.
        dynamodb (boto3.resource): The DynamoDB resource.
        table (boto3.resource.Table): The DynamoDB table.
    """
    
    def __init__(self, table_name, role_arn=None, role_session_name=None):
        self.table_name = table_name

        if role_arn and role_session_name:
            # Create an STS client
            sts = boto3.client('sts')

            # Assume the role
            try:
                print(f"Assuming role {role_arn}")
                assumed_role_object = sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=role_session_name
                )
            except (BotoCoreError, ClientError) as error:
                print(f"Failed to assume role: {error}")
                return

            # Extract the credentials
            credentials = assumed_role_object['Credentials']

            # Create a new session with the assumed role's credentials
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
            print(f"Assumed role {role_arn} successfully")
            print(f"Session expires at: {credentials['Expiration']}")
            print("creating dynamodb resource with assumed role credentials")
            self.dynamodb = session.resource('dynamodb')
        else:
            print("creating dynamodb resource with default credentials")
            self.dynamodb = boto3.resource('dynamodb')

        self.table = self.dynamodb.Table(table_name)

    def query_data(self, key_name, key_value):
        response = self.table.query(
            KeyConditionExpression=f'{key_name} = :value',
            ExpressionAttributeValues={
                ':value': key_value
            }
        )
        return response['Items']

    def query_index(self, index_name, key_name, key_value):
        response = self.table.query(
        IndexName=index_name,
        KeyConditionExpression=f'{key_name} = :value',
        ExpressionAttributeValues={
            ':value': key_value
        }
    )
        return response['Items']

    def scan_data(self, filter_expression=None):
        if filter_expression:
            response = self.table.scan(
                FilterExpression=filter_expression
            )
        else:
            response = self.table.scan()
        return response['Items']

    def insert_data(self, item):
        self.table.put_item(Item=item)
