Pre-requisites for Validation-phase-1 lambda:

NOTE:
The function needs to be setup as a separate lambda in AWS console.

1. Python-Terraform layer:
terraform-pkg.zip to be placed as layer

2. S3 bucket for script:
"validation-phase-1" S3 bucket used to store inspect.tf, output.tf, providers.tf, var.tf
Different bucket name to be used.

3. sns.tf (not to be inlcuded in s3) to be run before the lambda run to set up 2 SNS topics.
Subscribe your mailid(where you want to receive mail from lambda) to topics:
    1. assesment_complete_trigger
    2. inspector_finding_delivery

4. Lambda should have 256 MB CPU memory and runtime to be kept at 15 min(max. limit)

4. Role/policies for lambda:
EC2, Lambda, Inspector, cloudwatchevents, SSM