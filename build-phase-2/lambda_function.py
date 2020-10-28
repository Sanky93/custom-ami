from __future__ import print_function
import json
import boto3
import re
import os
import uuid
from packerpy import PackerExecutable
from botocore.exceptions import ClientError

download_dir = '/tmp/'

# get Account ID from lambda function arn in the context
account_id = boto3.client('sts').get_caller_identity().get('Account')

# current region
currentRegion = os.environ['AWS_REGION']

# destination lambda
dest_lambda = "terraform_test"


def lambda_handler(event, context):
    print('ENTERED BUILD LAMBDA')
    bucketName = ''
    configFileName = ''
    
    events = event.get('Records', [])
    print(events)
    if len(events) > 0:
        currentEvent = events[0]
        
        # reading from current event
        eventDetails = readEvent(currentEvent)
        bucketName = eventDetails[0]
        configFileName = eventDetails[1]

    if bucketName != '' and configFileName != '':
        
        # reading the config.json file
        config = readConfigFile(bucketName, configFileName)
        if config is not None:
            amiId = config['amiId']
            region = config['region']
            packerBucketName = config['bucketName']
            packerFile = config['packerFile']
            installScript = config['installScript']
            targetAmiId = config['targetAmiName']
            updateSSMID = config['amissmid']
            
            # downloading packer and custom install file
            downloadFile(packerBucketName, packerFile)
            downloadFile(packerBucketName, installScript)
            
            # running packer executable
            newAmi = invokePacker(region, packerFile, installScript, amiId, targetAmiId)
            if newAmi != '':
                
                # updating SSM parameter value
                update_ssm_parameter(updateSSMID, newAmi)
                
                # creating trigger for validation phase 1 lambda
                trigger_lambda()

            print('Exiting Lambda')
            return {
                'statusCode': 200,
                'body': json.dumps('AMI Creation Successful')
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('No AMI Config found')
            }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps('Couldnt retrieve S3 Object information')
        }
        
        
        
# reading from current event
def readEvent(currentEvent):
    bucketName = ''
    configFileName = ''
    if currentEvent['eventSource'] == 'aws:s3' and currentEvent['eventName'] == 'ObjectCreated:Put':
        bucketName = currentEvent['s3']['bucket']['name']
        configFileName = currentEvent['s3']['object']['key']    
    return bucketName, configFileName


# reading the config.json file
def readConfigFile(bucketName, configFileName):
    s3 = boto3.resource('s3')
    amiConfig = None
    # currentRegion = os.environ['AWS_REGION']
    content_object = s3.Object(bucketName, configFileName)
    file_content = content_object.get()['Body'].read().decode('utf-8')
    json_content = json.loads(file_content)
 
    for config in json_content['regionConfig']:
        if(config['region'] == currentRegion):
            amiConfig = config['amiConfig']
    return amiConfig
    

# downloading files from s3
def downloadFile(bucketName, fileName):
    s3Client = boto3.client('s3')
    try:
        s3Client.download_file(bucketName, fileName, f'{download_dir}{fileName}')
    except ClientError as e:
        return False


# running packer executable
def invokePacker(region, packerFile, installScript, amiBaseImage, targetAmiName):
    amivalue = ""
    pkr = PackerExecutable("/opt/python/lib/python3.8/site-packages/packerpy/packer")
    template = download_dir + packerFile
    installScriptFile = download_dir + installScript
    template_vars = {'baseimage': amiBaseImage, 'installScript': installScriptFile, 'targetAmiName':targetAmiName, 'region': region}
    (ret, out, err) = pkr.build(template, var=template_vars)
    
    outDecoded = out.decode('ISO-8859-1')
    print(outDecoded)
    if ret == 0:
        ami = re.search((':ami-[0-9][a-zA-Z0-9_]{16}'), outDecoded)
        amivalue = ami.group(0)
        amivalue = amivalue[1:]
    return amivalue
    

# updating SSM parameter value
def update_ssm_parameter(param, value):
    print(value)
    SSM_CLIENT = boto3.client('ssm')
    response = SSM_CLIENT.put_parameter(
        Name=param,
        Value=value,
        Type='String',
        Overwrite=True
    )

    if type(response['Version']) is int:
        return True
    else:
        return False


# creating trigger for validation phase 1 lambda
def trigger_lambda():
    id = uuid.uuid1()
    
    dest_lambda_arn = ":".join(["arn", "aws", "lambda", currentRegion, account_id, "function", dest_lambda])
    
    print("Lambda trigger created")

    client = boto3.client('events')
    rule_name = 'ssm_update_event'
    rule_res = client.put_rule(Name=rule_name, 
                    EventPattern= '''
                                    { 
                                    "source": [
                                        "aws.ssm"
                                    ],
                                    "detail-type": [
                                        "Parameter Store Change"
                                    ],
                                    "detail": {
                                        "name": [
                                            { "prefix": "ami-gold-" }
                                        ],
                                        "operation": [
                                            "Create",
                                            "Update"
                                        ]
                                    }
                                   }
                                   '''
                                   ,
                                   State='ENABLED',
                    Description="Find the event changes for SSM")
    
    print("res ==== ",rule_res)

        
    lambda_client = boto3.client('lambda')
    lambda_client.add_permission(
        FunctionName=dest_lambda_arn,
        StatementId=str(id),
        # StatementId=custom_app,
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_res['RuleArn']
    )


    response = client.put_targets(Rule='ssm_update_event',
                                   Targets=[
                                       {"Arn": dest_lambda_arn,
                                        "Id": '1'
                                        }])
    print("\nresponse ==== ",response)

    
