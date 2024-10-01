import requests
import json      
import boto3
from botocore.exceptions import ClientError



class OTRSRestAPI:
    """Summary class for interacting with the OTRS REST API.
        example: var = otrsapi = OTRSRestAPI("https://restapi.com/api/v1/example")  
        Replace with your API base URL                        
        import__ from jsonimport import OTRSRestAPI
        
        .update_data(update_data) # Update Data
        
        .search_data(search_query) # Search Data
        
        .get_token(credentials) # Get Access Token   send credentials as json.  
    """
    def __init__(self, base_url):
        self.base_url = base_url
        
        # Create a Secrets Manager client
        client = boto3.client('secretsmanager')

        # Retrieve the secret value
        response = client.get_secret_value(SecretId='prd/itsm/cmdbapikey')

        # Parse the secret value JSON string and store it in self.secret
        self.secret = json.loads(response['SecretString'])
        #print(self.secret)
        self.token = self.get_token()

    def update_data(self, data):
        print("updating cmdb")
        url = f"{self.base_url}/Update"
        data.update(self.secret)
        response = requests.post(url, json=data, verify=False, headers={'Content-Type': 'application/json'})
        print(response.json())
        return response.json()
    
    def create_data(self, data):
        print("updating cmdb")
        url = f"{self.base_url}/Create"
        response = requests.post(url, json=data, verify=False, headers={'Content-Type': 'application/json'})
        print(response.json())
          # Pause the program for 5 seconds
       
        return response.json()
    
    def get_data(self, data):
        print("geting cmdb data")
        url = f"{self.base_url}/Get"
        data.update(self.secret)
        response = requests.post(url, json=data, verify=False, headers={'Content-Type': 'application/json'})
        print(response.json())
          # Pause the program for 5 seconds
       
        return response.json()

    def search_data(self, data):
        print("sending search data to cmdb")
        data.update(self.secret)
        url = f"{self.base_url}/Search"
        response = requests.get(url, json=data, verify=False, headers={'Content-Type': 'application/json'})
        #print(response.json())
        return response.json()

    def get_token(self):
        url = f"{self.base_url}/AccessToken"
        response = requests.post(url, data= json.dumps(self.secret), verify=False, headers={'ContentType': "application/json"} )
        print(response.json)
        self.access_token = response.json()
        return self.access_token
    





class ConfigItem:
    def __init__(self, item,otrs_api=None):
        self.item = item
        self.otrs_api = otrs_api
        #self.token = self.otrs_api.get_token()

    def to_dict(self):
        
    
    
        nonprodprefixes = ["cloud9", "tst", "dev", "test", "qa", "stage", "stg", "sbx", "uat", "sandbox","npr","nonprod","np","td","temp","tmp"]
        prodprefixes= ["prd", "prod", "production","mc","ss"]

        nametag = self.item.get('nametag', '').lower()
        depl_state = "Production" if any(nametag.startswith(prefix) for prefix in prodprefixes) else "Test/QA"

        critical_state_lookup = {
        'mc': 'Mission Critical',
        'dr': 'Disaster Recovery',
        'ss': 'Support Systems',
        'pc': 'proof of concept',
        'td': 'Test & Development'
        }

        critical_state = next((critical_state_lookup[prefix] for prefix in critical_state_lookup if nametag.startswith(prefix)), "")





        result = {
            'AccessToken': self.get('token'),
            'ConfigItem': {
                'Class': "Server",
                'Name': self.item.get('nametag'),
                'DeplState': depl_state,
                'InciState': "Operational",
                'CIXMLData': {
                    'SerialNumber': self.item.get('resourceid'),
                    'FQDN': self.item.get('fqdn'),
                    'Criticality': critical_state,
                    'Type': "Virtual",
                    'CPU': self.item.get('cpu'),
                    'OperatingSystem': self.item.get('PlatformName'),
                    'BackupIsActive': "No",
                    'Memory': self.item.get('memory'),
                    'IP': self.item.get('privateIpAddress'),
                    'Note': self.item.get('stateName'),
                    'Location': self.item.get('availabilityZone'),
                }
            }
        }

        vols_dict = self.item.get('disk', [])
        for i, vol in enumerate(vols_dict):
            print((i+1),vol)

            #{'resourceId': 'vol-098eadb86e3a39178', 'configuration': {'volumeType': 'gp3', 'size': '4500.0', 'iops': '9000.0'}}
            vol_details = vol['resourceId'] + ':' + str(vol['configuration']['size'])
            result['ConfigItem']['CIXMLData'][f'Disk::{i+1}'] = vol_details

        return result
            
    def create_search_json(self):
        print("creating search cmdb json")
        #token = self.otrs_api.get_token()
        searchjson= {

            'ConfigItem': {
                'AccessToken': self.get('token'),
                'Class': "Server",
                'Name': self.item.get('nametag'),
                'InciState': "Operational"
            }
        }
        
        #searchjson = json.dumps(searchjson)
        #print(searchjson)
        return searchjson