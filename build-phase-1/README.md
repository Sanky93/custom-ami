Prerequisites for build-phase-1 lambda:

NOTE:
The function needs to be setup as a separate lambda in AWS console.

1. Cloudwatch Event Trigger for initiating build-phase-1 lambda to be terraformed w.r.t to any update to the SSM paramater create or update event.

2. Apart from lambda_function.py, all files need to be kept in S3 bucket.
S3 bucket to be created to keep other files (.json and .sh files)

3. Role/policies for lambda:
S3, Lambda, cloudwatchevents, SSM