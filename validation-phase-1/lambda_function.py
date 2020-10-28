import os
import boto3
import uuid

from python_terraform import *

# S3 Bucket name
BUCKET_NAME = 'validation-phase-1'

# AWS current region
region = os.environ['AWS_REGION']

# Download directory for S3
download_dir = '/tmp/'

# SNS topic
SNS_TOPIC = "assesment_complete_trigger"

# Destnation lambda
dest_lambda = "validation-2"




def lambda_handler(event, context):
    
    print(event)
    ssmValue = event['detail']['name']
    account_id = event['account']
    
    print(ssmValue)
    print(account_id)
        
    # os.system('cp /var/task/{*.tf,lambda_function.py} /tmp/')
    
    s3 = boto3.resource('s3')
    s3Client = boto3.client('s3')
    try:
        my_bucket = s3.Bucket(BUCKET_NAME)
        for s3_object in my_bucket.objects.all():
          filename = s3_object.key
          s3Client.download_file(BUCKET_NAME, filename, f'{download_dir}{filename}')
    except ClientError as e:
        return False
    
    # get ami id from SSM parameter
    ami_id = get_ami_id(ssmValue)
    print(ami_id)
    
    # Execute terraform scripts for assessment run and fetch template arn as output
    output = execute(region,ami_id)
    template_arn = output['template_arn']['value']
    print("template_arn ===== ", template_arn)
    
    # subscribe to SNS based event
    subscribe_to_event(template_arn, account_id)
    
    # creating trigger for validation phase 2 lambda 
    trigger_lambda(account_id)
    
    # Running assessment template and tagging template
    start_assessment_run(template_arn, ssmValue)
    

# get ami id from SSM parameter    
def get_ami_id(ssmValue):
    client = boto3.client('ssm')
    
    response = client.get_parameter(
    Name=ssmValue,
    WithDecryption=True
    )
    return (response['Parameter']['Value'])
    
    
# Execute terraform scripts for assessment
def execute(region,ami_id):
        print("In Execution() ---",ami_id)
        tf = Terraform(working_dir="/tmp/",terraform_bin_path='/opt/python/lib/python3.8/site-packages/terraform',variables={"region": region, "AMI_ID": ami_id})
        tf.init()
        approve = {"auto-approve": True}
        tf.apply(capture_output=True, skip_plan=True, **approve)
        stdout=tf.output()
        return stdout
    

# subscribe to SNS based event  
def subscribe_to_event(template_arn, account_id):

    # client representing
    inspector = boto3.client('inspector')
    sns = boto3.client('sns')

    # To create topic ARN using regular expression
    topic_arn = ":".join(["arn", "aws", "sns", region, account_id, SNS_TOPIC])

    # Subscribing sns with template, event based
    events = ['ASSESSMENT_RUN_COMPLETED']  # ,'FINDING_REPORTED','ASSESSMENT_RUN_STATE_CHANGED','ASSESSMENT_RUN_STARTED', ]
    for event in events:
        event_response = inspector.subscribe_to_event(resourceArn=template_arn, event=event, topicArn=topic_arn)
        
    

# creating trigger for validation phase 2 lambda 
def trigger_lambda(account_id):
    id = uuid.uuid1()
    # To create topic ARN using regular expression
    topic_arn = ":".join(["arn", "aws", "sns", region, account_id, SNS_TOPIC])
    dest_lambda_arn = ":".join(["arn", "aws", "lambda", region, account_id, "function", dest_lambda])
    
    sns = boto3.client('sns')
    
    sns.subscribe(
    TopicArn=topic_arn,
    Protocol='lambda',
    Endpoint=dest_lambda_arn
    )

    # To create lambda trigger for SNS
    lambda_client = boto3.client('lambda')

    lambda_client.add_permission(
        FunctionName=dest_lambda_arn,
        StatementId=str(id),
        Action='lambda:InvokeFunction',
        Principal='sns.amazonaws.com',
        SourceArn=topic_arn
    )
    

# Running assessment template and tagging template
def start_assessment_run(arn, ssmValue):
    client = boto3.client('inspector')
    
    # running assessment te
    response = client.start_assessment_run(
        assessmentTemplateArn=arn,
        assessmentRunName='Gold_AMI_Assessment_Run'
    )
    
    # tagging template
    client.set_tags_for_resource(
    resourceArn=arn,
    tags=[
            {
                'key': 'ami-name',
                'value': ssmValue
            },
         ]
    )