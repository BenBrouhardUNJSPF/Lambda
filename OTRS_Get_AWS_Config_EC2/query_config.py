import boto3







class AWSConfigQuery:
    def __init__(self, role_arn='arn:aws:iam::038844963580:role/Shared_Services_Lambda_cross_account_access'):
        self.role_arn = role_arn
        self.client = self.assume_role()

    def assume_role(self):
        sts_client = boto3.client('sts')
        assumed_role_object = sts_client.assume_role(
            RoleArn=self.role_arn,
            RoleSessionName="AssumeRoleSession1"
        )
        credentials = assumed_role_object['Credentials']
        return boto3.client(
            'config',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

    def execute_query(self, query,ca_name='aws-controltower-ConfigAggregatorForOrganizations'):
        
        args = {    'Expression':query,
                    'ConfigurationAggregatorName':ca_name,
                    'Limit':100
                } 
        response = self.client.select_aggregate_resource_config(**args)
               
        return response['Results']
        #return self.client.select_aggregate_resource_config(**args)

            
        