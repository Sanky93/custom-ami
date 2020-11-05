from __future__ import print_function
import json
import boto3
import os
import uuid
from botocore.exceptions import ClientError

BUCKET_NAME = 'demos-s3-lambda1'

# get Account ID
account_id = boto3.client('sts').get_caller_identity().get('Account')

# current region
currentRegion = os.environ['AWS_REGION']

# destination lambda
dest_lambda = "multi-ami-build-2"


def lambda_handler(event, context):
    ssmKey = event['detail']['name']
    ssm = boto3.client('ssm')
    
    # get ssm parameter value
    ssm_parameter = ssm.get_parameter(Name=ssmKey, WithDecryption=True)
    ssmValue = ssm_parameter['Parameter']['Value']
    print(ssmKey) 
    print(ssmValue)
    
    # creating trigger to initiate build phase 2 lambda
    # s3_trigger()
    
    # downloading files from s3 bucket
    download_file(BUCKET_NAME, ssmValue)



# downloading files from s3 bucket
def download_file(BUCKET_NAME, ssmValue): 
    s3 = boto3.resource('s3')
    s3Client = boto3.client('s3')

    try:
        filesResponse = s3Client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="ami")
        for s3_object in filesResponse['Contents']:
            if s3_object['Key'].endswith(("config.json", "_files")): 
                filename = s3_object['Key']
                s3object = s3.Object(BUCKET_NAME, filename)   
                body = s3object.get()['Body'].read()
                configData = json.loads(body)

                for amiConfig in configData['regionConfig']:                    
                    amiConfig['amiConfig']['amiId'] = ssmValue

                s3object.put(
                    Body=(bytes(json.dumps(configData).encode('UTF-8')))
                )    
    except ClientError as e:
        return False


# creating trigger to initiate build phase 2 lambda
def s3_trigger():
    id = uuid.uuid1()
    
    bucket_arn = ":".join(["arn", "aws", "s3", "", "", BUCKET_NAME])
    dest_lambda_arn = ":".join(["arn", "aws", "lambda", currentRegion, account_id, "function", dest_lambda])
    
    # adding trigger for build phase 2 lambda
    lambda_client = boto3.client('lambda')
    lambda_client.add_permission(
        FunctionName=dest_lambda_arn,
        StatementId=str(id),
        Action='lambda:InvokeFunction',
        Principal='s3.amazonaws.com',
        SourceArn=bucket_arn,
        SourceAccount=account_id
    )
    
    # adding s3 notification event in s3 bucket
    s3 = boto3.resource('s3')
    bucket_notification = s3.BucketNotification(BUCKET_NAME)
    response = bucket_notification.put(
                NotificationConfiguration={
                    'LambdaFunctionConfigurations': [
                        {
                            'LambdaFunctionArn': dest_lambda_arn,
                            'Events': [
                                's3:ObjectCreated:*'
                            ],
                            'Filter': {
                                'Key': {
                                    'FilterRules': [
                                        {
                                            'Name': 'suffix',
                                            'Value': 'config.json'
                                        },
                                    ]
                                }
                            }
                        },
                ]})
