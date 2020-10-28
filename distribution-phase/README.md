NOTE:
The function needs to be setup as a separate lambda in AWS console

1. Account IDs to be modified as per AWS account used.

2. dist-ami-policy.json content to be added as a policy to the distribution-phase lambda role.

3. crossAccountAMI-Role role to be created in destination account.

4. crossAccountAMI-Role.json to be added as a policy to crossAccountAMI-Role role in destination account.

5. trust_policy.json content to be added to trust relationship in crossAccountAMI-Role role.

3. Role/policies for lambda:
Lambda, cloudwatchevents, SSM, IAM, STS, EC2

