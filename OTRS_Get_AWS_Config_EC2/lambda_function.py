"""
Lambda Function for AWS Config and OTRS Integration

This script performs the following steps:

1. Query AWS Config for instances.
2. For each instance, query OTRS to get the Config ID.
3. Query OTRS again to get all information for each Config ID.
4. Compare the information from AWS Config to OTRS.
5. If the information is not accurate, update OTRS.

Author: Brouhard
Date: 2024-04-18
Company: UNJSPF
Version: 1.0.0

#todo:
1. functions for update and create
2. trigger from cloudwatch events and config rule
3. add logging
4. add error handling
5. trigger from cloudformation
6. add tests

"""


import json
import boto3
import datetime
from decimal import Decimal
from compare_data import compare_data
from datetime import datetime
from query_config import AWSConfigQuery
from dyndb import DynamoDBClient
from update_otrs import OTRSRestAPI, ConfigItem
from botocore.exceptions import BotoCoreError, ClientError
from email_template import create_table, add_horizontal_line,send_email, create_html_header, create_html_footer


# def send_email(subject, body, from_addr, to_addr):
#     ses_client = boto3.client('ses')
#     try:
#         response = ses_client.send_email(
#             Source=from_addr,
#             Destination={
#                 'ToAddresses': [to_addr]
#             },
#             Message={
#                 'Subject': {
#                     'Data': subject
#                 },
#                 'Body': {
#                     'Text': {
#                         'Data': body
#                     }
#                 }
#             }
#         )
#     except (BotoCoreError, ClientError) as error:
#         print(f'Failed to send email: {error}')
#         return False

#     return True

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
    
def convert_floats_to_strings(d):
    for key, value in d.items():
        if isinstance(value, float):
            d[key] = str(value)
        elif isinstance(value, dict):
            d[key] = convert_floats_to_strings(value)
    return d

def get_aws_instance_information(instance_types):
    rows = []
    client = boto3.client("ec2")

   
    
    filter=[]
    for type in instance_types:
   
        type=type.replace("'","")
        #print(type)
        #print(lookup_table.get(type))
        filter.append(type)
    

        #print(client.describe_instance_types(InstanceTypes=filter))
    args = {'InstanceTypes':filter}
    
    while True:
        result = client.describe_instance_types(**args)

        for instance in result["InstanceTypes"]:
            num_cpus = instance["VCpuInfo"]["DefaultVCpus"]
            num_gpus = sum(
                gpu["Count"] for gpu in instance.get("GpuInfo", {"Gpus": []})["Gpus"]
            )
            memory = instance["MemoryInfo"]["SizeInMiB"]
            memoryGB = memory / 1024
            memoryGB = Decimal(str(memoryGB))
            processor = instance.get("ProcessorInfo").get("SustainedClockSpeedInGhz")
            
            rows.append(
                {
                    "instance": instance["InstanceType"],
                    "cpus": num_cpus,
                    "gpus": num_gpus,
                    "memorygb": memoryGB,
                    "memorymb": memory,
                    "processorspeed": processor
                }
            )

        if "NextToken" not in result:
            break

        args["NextToken"] = result["NextToken"]
    
    lookup_table = {row['instance']: row for row in rows}
    return lookup_table

def ssm_query(instance_id):
    query_ssm_type = f"""
    SELECT
    resourceId,
    configuration
    WHERE
    resourceType = 'AWS::SSM::ManagedInstanceInventory'
    and resourceId = '{instance_id}'
    """
    return query_ssm_type
    
def vol_query(instance_id):
    query_ssm_type = f"""
    SELECT
      resourceId,
      configuration.volumeType,
      configuration.size,
      configuration.iops
    WHERE
      resourceType = 'AWS::EC2::Volume'
      and configuration.attachments.instanceId = '{instance_id}'
      """
      
    return query_ssm_type

def process_instance(results, instance_table, recorded_date, aws_config_query, ssm_query, vol_query):
    items = []
    for i in range(len(results)):
        
        platform_name = 'unknown'
        ssmresults = None
        fqdn = None   
        
        
        
        instance = convert_floats_to_strings(json.loads(results[i]))
        resourceId = instance.get('resourceId')
        print(f"checking: {resourceId}")
        resourceconfig = instance.get('configuration')
        tags = instance.get('tags', [])
        nametag = None
        for tag in tags:
            if tag.get('key') == 'Name':
                nametag = tag.get('value')
                break
        print(f"found name: {nametag}")

            
        ssmresults = aws_config_query.execute_query(ssm_query(resourceId))
        if ssmresults:
            ssmresults = json.loads(ssmresults[0])
            ssmresultsconf = ssmresults.get('configuration')
            ssmresultsinstinfo = ssmresultsconf.get('AWS:InstanceInformation').get('Content')
            if ssmresultsinstinfo is not None and ssmresultsinstinfo.get(resourceId) is not None:
                platform_name = ssmresultsinstinfo.get(resourceId).get('PlatformName')

            if 'windows' in platform_name.lower():
                ssmwinpatchinfo = ssmresultsconf.get('AWS:WindowsUpdate').get('Content')
            fqdn = ssmresultsinstinfo.get(resourceId).get('ComputerName', 'none')
        vols_dict = []
        volsresults = aws_config_query.execute_query(vol_query(resourceId))
        for vol in volsresults:
            vol_dict = convert_floats_to_strings(json.loads(vol))
            vols_dict.append(vol_dict)
        if volsresults:
            volresults = json.loads(volsresults[0])
            volresultsconf = volresults.get('configuration')
            vol_size = Decimal(str(volresultsconf.get('size')))
            vol_iops = Decimal(str(volresultsconf.get('iops')))
        else:
            volresults= 0
        instancetype = resourceconfig.get('instanceType')
        # if ssmresultsinstinfo is not None and ssmresultsinstinfo.get(resourceId) is not None:
        #     platform_name = ssmresultsinstinfo.get(resourceId).get('PlatformName')
        # else:
        #     platform_name = 'unknown'
        item = {
            'recorded_date': recorded_date,
            'resourceid': resourceId,
            'arn': instance.get('arn'),
            'availabilityZone': instance.get('availabilityZone'),
            'accountId': instance.get('accountId'),
            'stateName': instance.get('configuration', {}).get('state', {}).get('name'),
            'instanceType': instance.get('configuration', {}).get('instanceType'),
            'resourceCreationTime': instance.get('resourceCreationTime'),
            'privateIpAddress': instance.get('configuration', {}).get('networkInterfaces', [{}])[0].get('privateIpAddress'),
            'publicIpAddress': instance.get('configuration', {}).get('networkInterfaces', [{}])[0].get('publicIpAddress'),
            'cpu': instance_table[instancetype]['cpus'],
            'memory': instance_table[instancetype]['memorygb'],
            'tags': tags,
            'PlatformName': platform_name,
            'FQDN': fqdn,
            'disk': vols_dict,
            'nametag': nametag
        }
        items.append(item)
    return items

def get_account_name(orgclient, account_id):
    try:
        response = orgclient.describe_account(AccountId=account_id)
        return response['Account']['Name']
    except Exception as e:
        print(f"Error getting account name for account ID {account_id}: {e}")
        return None

def lambda_handler(event, context):
    to_email=['brouhard@un.org', 'yannick.soumbou@un.org', 'unjspf-itsm@un.org']
    dynodbtable= 'otrs_config_history'
    recorded_date= datetime.now().strftime('%Y-%m-%d')
    dynoclient = DynamoDBClient(dynodbtable)
    orgclient = boto3.client('organizations')
    HEADER_TEXT = 'UNJSPF data import error report \n\n'
    # ec2= boto3.client('ec2')
    
    
    aws_config_query = AWSConfigQuery()

    
    otrsapi = OTRSRestAPI("https://itsm.unjspf.org/otrs/nph-genericinterface.pl/Webservice/CMDBServerClass")  # Replace with your API base URL
    # prefix list for non production instances.
    #nonprodprefixes = ["cloud9", "tst", "dev", "test", "qa", "stage", "stg", "sbx", "uat", "sandbox","npr","nonprod","np"]

 

    
    query_ec2_instances = """
        SELECT
    resourceId,
    arn,
    availabilityZone,
    accountId,
    
    configuration.state.name,
    configuration.instanceType,
    configuration.networkInterfaces.networkInterfaceId,
    configuration.networkInterfaces,
    resourceCreationTime,
    tags.value,
    tags
    WHERE
    resourceType = 'AWS::EC2::Instance'"""
  


    print("running querys")
    #test instace
    #instance_id = 'i-000f8426ffc319c0c'
    
    #instance_types = aws_config_query.execute_query(query_instance_type)
    results= aws_config_query.execute_query(query_ec2_instances)

    

    items = []
    create_jsons=[]
    # create search item
    search_result= {}
    print("starting to process results")
    #get instanctype list.
    
    instance_types = [json.loads(results[i]).get('configuration', {}).get('instanceType') for i in range(len(results))]
    instance_table=get_aws_instance_information(instance_types)
    
    
    
    items = process_instance(results, instance_table, recorded_date, aws_config_query, ssm_query, vol_query)           
          
                 
        
        #TODO:
        # 1. compare the data in dynomdo from the day before. 
        # 2. if the data is the same, do not update the data.
        
        
        
        ######## Add the data to the dynomo Db table  
        
    errors = [{
                'resourceid': [],
                'message': [],
                'AZ': [],
                'accountid': []
            } ]
          
    count=0
    error_count = 0
    error_list = []
    error_message = []       
    for item in items:
    #     print(json.dumps(item,items) 
    #     print(" \n ")
    #           ######## Add the data to the dynomo Db table  
        nametag = item.get('nametag')
        
        
        if nametag and nametag.strip():       
            try:
                dynoclient.insert_data(item)
                count +=1 

            except Exception as e:
                error_count +=1
                error_list.append(item['resourceid'])  
                errors[-1]['resourceid'].append(item['resourceid'])  
                errors[-1]['message'].append(e)
                errors[-1]['AZ'].append(item['availabilityZone'])  # Assuming 'AZ' and 'accountid' are keys in the item
                errors[-1]['accountid'].append(item['accountId'])
            #     send_email(
            # subject=f'Insert Failed: {dynodbtable}: {recorded_date}',
            # body=f' when trying to update table: {dynodbtable} \n Failed to insert data: {e} \n {item}',
            # from_addr='lamdba-dynamodb-update@unjspf.org',
            # to_addr=to_email
            # )   
        else:
            error_count +=1
            error_list.append(item['resourceid'])  
            error_message.append(f"insert Failed due to missing name tag: {item['resourceid']} : region: {item['availabilityZone']}, Account: {item['accountId']}")  
            errors[-1]['resourceid'].append(item['resourceid'])  
            errors[-1]['message'].append('insert Failed due to missing name tag')
            errors[-1]['AZ'].append(item['availabilityZone'])  # Assuming 'AZ' and 'accountid' are keys in the item
            errors[-1]['accountid'].append(item['accountId'])
                        
            
            # send_email(
            #     subject=f'Ec2 without name key.  DB insert Failed: {item['resourceid']}',
            #     body=f' DB insert Failed: {item['resourceid']} : region: {item['availabilityZone']}, Account: {item['accountId']} \n Failed to insert data: {item}',
            #     from_addr='lamdba-dynamodb-update-no_nametag@unjspf.org',
            #     to_addr=to_email
            #     )   
            
    #header = [ 'recorded_date', 'resourceid', 'availabilityZone', 'accountId' ]   
    header = list(errors[0].keys())
    # for error_dict in errors:
    #     for key in error_dict:
    #         header.append(key)
    email_body = create_html_header(HEADER_TEXT )
    #email_body += add_horizontal_line('', '-', 130)
    email_body += create_table(header, errors, 'Issues', 130)

    #email_body += add_horizontal_line('', '-', 130)
    # i = 0
    # while i < len(error_list):
    #     emlen = len(error_message[i]) + 20
    #     # email_body += add_horizontal_line('', '-', emlen)
    #     email_body += f"Error:  {error_list[i]} \n {error_message[i]}  \n"
    #     email_body += add_horizontal_line('', '-', emlen)
        
    #     # email_body += f"Error:  {error_list[i]} \n {error_message[i]}  \n"
    #     # email_body += add_horizontal_line('', '-', emlen)
    #     i += 1
    
    footer_text = f"\nTotal records inserted: {count} \nTotal errors: {error_count}"
    email_body += create_html_footer(footer_text)
                      
    if error_count > 0:
        send_email(
            subject=f'Insert Failed: {dynodbtable}: {recorded_date}',
            body=email_body,
            from_addr='lamdba-dynamodb-update@unjspf.org',
            to_addr=to_email
        )

    return {
        'statusCode': 200,
        #'instances': items,
        #'access_token' :  otrsapi.access_token,
        'update_count': count,
        'error': error_count
        #'resourceid':  item['resourceId'],
        # 'instanceType': item['instanceType'],
        # 'availabilityZone': item['availabilityZone'],
        # 'accountId': item['accountId'],
        # #'configuration': item['configuration'],
        # 'StateName': item['StateName'],
        # 'resourceCreationTime': item['resourceCreationTime']
        
            }
