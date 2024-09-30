import boto3
import os

# Initialize boto3 clients
s3_client = boto3.client('s3')
ec2_client = boto3.resource('ec2')
elbv2_client = boto3.client('elbv2')
autoscaling_client = boto3.client('autoscaling')
sns_client = boto3.client('sns')
lambda_client = boto3.client('lambda')

# Check if the S3 bucket exists
def check_s3_bucket_exists(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f'S3 bucket "{bucket_name}" already exists.')
        return True
    except:
        print(f'S3 bucket "{bucket_name}" does not exist. Creating bucket...')
        return False

# Create an S3 bucket to store static files
def create_s3_bucket(bucket_name, region='us-west-2'):
    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        print(f'S3 bucket "{bucket_name}" created.')
    except Exception as e:
        print(f'Error creating bucket: {e}')

# Upload the static HTML file to the S3 bucket
def upload_static_file_to_s3(bucket_name, file_path, file_name):
    try:
        s3_client.upload_file(file_path, bucket_name, file_name)
        print(f'File "{file_name}" uploaded to S3 bucket "{bucket_name}".')
    except Exception as e:
        print(f'Error uploading file: {e}')

# Launch EC2 instances and configure them as web servers with Nginx (for Ubuntu)
def launch_ec2_instances(bucket_name, file_name, instance_count):
    try:
        instances = ec2_client.create_instances(
            ImageId='ami-05134c8ef96964280',  # Ubuntu 22.04 LTS AMI (x86_64)
            MinCount=instance_count,
            MaxCount=instance_count,
            InstanceType='t2.micro',  # Instance type with x86_64 architecture
            KeyName='Aditya-pem',  # Replace with your key pair
            SecurityGroupIds=['sg-057f0e6c8849c7ff8'],  # Replace with your security group ID
            UserData=f"""#!/bin/bash
            sudo apt-get update -y
            sudo apt-get install -y nginx
            sudo snap install aws-cli --classic
            aws configure set aws_access_key_id <xxxxxxxxxxxxxxx>
            aws configure set aws_secret_access_key <xxxxxxxxxxxxxxxxxx>
            aws configure set region us-west-2
            aws configure set output json
            sudo systemctl start nginx
            sudo systemctl enable nginx
            sudo aws s3 cp s3://{bucket_name}/{file_name} /var/www/html/
            sudo chown -R www-data:www-data /var/www/html
            sudo chmod -R 755 /var/www/html
            sudo systemctl restart nginx
            """
        )

        for idx, instance in enumerate(instances):
            instance.create_tags(Tags=[{"Key": "Name", "Value": f"Aditya-EC2-Instance-{idx + 1}"}])
            print(f'Launching EC2 instance {instance.id}...')

        for instance in instances:
            instance.wait_until_running()
            instance.reload()
            print(f'EC2 instance {instance.id} is now running at {instance.public_ip_address}')
            
        return instances  # Return the list of instances for load balancer registration
    except Exception as e:
        print(f'Error launching EC2 instances: {e}')
        return []

# Create an Application Load Balancer (ALB) and Target Group
def create_load_balancer(instances):
    try:
        target_group = elbv2_client.create_target_group(
            Name='Aditya-Target-Group',
            Protocol='HTTP',
            Port=80,
            VpcId='vpc-0321f38a7b594180d',
            TargetType='instance'
        )

        target_group_arn = target_group['TargetGroups'][0]['TargetGroupArn']

        targets = [{'Id': instance.id} for instance in instances]
        elbv2_client.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=targets
        )

        load_balancer = elbv2_client.create_load_balancer(
            Name='Aditya-ALB',
            Subnets=['subnet-03ca36de9a927fe8e', 'subnet-09bd0e0acc92d4efa'],
            SecurityGroups=['sg-057f0e6c8849c7ff8'],
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4'
        )

        lb_arn = load_balancer['LoadBalancers'][0]['LoadBalancerArn']

        elbv2_client.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{'Type': 'forward', 'TargetGroupArn': target_group_arn}]
        )

        dns_name = load_balancer['LoadBalancers'][0]['DNSName']
        print('Application Load Balancer created and instances registered.')
        print(f'DNS Name of the Load Balancer: {dns_name}')
        return dns_name
    except Exception as e:
        print(f'Error creating Load Balancer: {e}')
        return None

# Create an Auto Scaling Group (ASG) and attach scaling policies
def create_auto_scaling_group(instance_ids):
    try:
        # Step 1: Create Launch Template for EC2 instance configuration
        launch_template = elbv2_client.create_launch_template(
            LaunchTemplateName='Aditya-Launch-Template',
            LaunchTemplateData={  
                'ImageId': 'ami-05134c8ef96964280',  # Ubuntu 22.04 LTS AMI
                'InstanceType': 't2.micro',
                'KeyName': 'Aditya-pem',
                'SecurityGroupIds': ['sg-057f0e6c8849c7ff8'],
                'UserData': f"""#!/bin/bash
                # Update package list
                sudo apt-get update -y

                # Install Nginx
                sudo apt-get install -y nginx

                # Install AWS CLI version 2
                sudo snap install aws-cli --classic

                # Run AWS configure command to set credentials
                aws configure set aws_access_key_id <xxxxxxxxxxxxxxxxxxxxxxxxxxxxx>
                aws configure set aws_secret_access_key <xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx>
                aws configure set region us-west-2
                aws configure set output json

                # Start and enable Nginx
                sudo systemctl start nginx
                sudo systemctl enable nginx

                # Fetch static file from S3 bucket with sudo
                sudo aws s3 cp s3://{bucket_name}/{file_name} /var/www/html/

                # Set proper permissions for Nginx
                sudo chown -R www-data:www-data /var/www/html
                sudo chmod -R 755 /var/www/html

                # Restart Nginx to apply changes
                sudo systemctl restart nginx
                """
            }
        )
        
        launch_template_id = launch_template['LaunchTemplate']['LaunchTemplateId']

        # Step 2: Create Auto Scaling Group
        autoscaling_client.create_auto_scaling_group(
            AutoScalingGroupName='Aditya-ASG',
            LaunchTemplate={'LaunchTemplateId': launch_template_id, 'Version': '$Latest'},
            MinSize=1,
            MaxSize=3,
            DesiredCapacity=1,
            VPCZoneIdentifier='subnet-03ca36de9a927fe8e,subnet-09bd0e0acc92d4efa'  # Replace with your subnet IDs
        )

        # Step 3: Configure Scaling Policy (Scale out when CPU > 70%)
        autoscaling_client.put_scaling_policy(
            AutoScalingGroupName='Aditya-ASG',
            PolicyName='ScaleOutPolicy',
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization'
                },
                'TargetValue': 70.0
            }
        )

        print('Auto Scaling Group and scaling policies created.')
    except Exception as e:
        print(f'Error creating Auto Scaling Group: {e}')
        
# Create SNS topics for notifications
def create_sns_topics():
    try:
        # Create SNS Topic for Health Issues
        health_topic = sns_client.create_topic(Name='Aditya-HealthIssues')
        health_topic_arn = health_topic['TopicArn']
        print(f'SNS Topic for Health Issues created: {health_topic_arn}')

        # Create SNS Topic for Scaling Events
        scaling_topic = sns_client.create_topic(Name='Aditya-ScalingEvents')
        scaling_topic_arn = scaling_topic['TopicArn']
        print(f'SNS Topic for Scaling Events created: {scaling_topic_arn}')

        # Create SNS Topic for High Traffic
        traffic_topic = sns_client.create_topic(Name='Aditya-HighTraffic')
        traffic_topic_arn = traffic_topic['TopicArn']
        print(f'SNS Topic for High Traffic created: {traffic_topic_arn}')

        return {
            'health_topic_arn': health_topic_arn,
            'scaling_topic_arn': scaling_topic_arn,
            'traffic_topic_arn': traffic_topic_arn
        }

    except Exception as e:
        print(f'Error creating SNS topics: {e}')
        return {}

# SNS Notifications Setup
def setup_sns_notifications():
    try:
        health_topic = sns_client.create_topic(Name='HealthIssuesTopic')
        scaling_topic = sns_client.create_topic(Name='ScalingEventsTopic')
        high_traffic_topic = sns_client.create_topic(Name='HighTrafficTopic')

        print('SNS Topics Created:')
        print(f'- Health Issues Topic ARN: {health_topic["TopicArn"]}')
        print(f'- Scaling Events Topic ARN: {scaling_topic["TopicArn"]}')
        print(f'- High Traffic Topic ARN: {high_traffic_topic["TopicArn"]}')

        # Setup subscriptions (replace with valid email/SMS numbers)
        sns_client.subscribe(
            TopicArn=health_topic['TopicArn'],
            Protocol='email',  # or 'sms'
            Endpoint='adityavakharia@gmail.com'  # Replace with your email or phone number
        )

        sns_client.subscribe(
            TopicArn=scaling_topic['TopicArn'],
            Protocol='email',
            Endpoint='your-email@example.com'
        )

        sns_client.subscribe(
            TopicArn=high_traffic_topic['TopicArn'],
            Protocol='email',
            Endpoint='adityavakharia@gmail.com'
        )

        print('SNS subscriptions created for health, scaling, and traffic alerts.')
    except Exception as e:
        print(f'Error setting up SNS notifications: {e}')

# Function to publish a message to SNS topics
def publish_to_sns(topic_arn, message):
    try:
        sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject='AWS Notification'
        )
        print(f'Message published to SNS Topic: {topic_arn}')
    except Exception as e:
        print(f'Error publishing message to SNS: {e}')

# Create SNS topics and return their ARNs
sns_topic_arns = create_sns_topics()

# Lambda integration to handle SNS notifications
def create_lambda_for_notifications():
    try:
        lambda_client = boto3.client('lambda')
        
        # Create the Lambda function to handle EC2 health, scaling, and traffic alerts
        lambda_function = lambda_client.create_function(
            FunctionName='Aditya-NotificationHandler',
            Runtime='python3.8',
            Role='arn:aws:iam::123456789012:role/lambda-execution-role',  # Replace with your IAM role for Lambda
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': b'fileb://path-to-your-lambda-function.zip'},  # Update path with your zipped function
            Environment={
                'Variables': {
                    'HEALTH_ISSUE_TOPIC_ARN': sns_topic_arns['health_topic_arn'],
                    'SCALING_EVENT_TOPIC_ARN': sns_topic_arns['scaling_topic_arn'],
                    'HIGH_TRAFFIC_TOPIC_ARN': sns_topic_arns['traffic_topic_arn']
                }
            }
        )
        print(f"Lambda function created with ARN: {lambda_function['FunctionArn']}")

    except Exception as e:
        print(f'Error creating Lambda function: {e}')


# Tear down function to clean up all resources
def tear_down():
    try:
        # Deleting Load Balancer
        try:
            print("Deleting Load Balancer...")
            elbv2_client.delete_load_balancer(LoadBalancerArn='Aditya-ALB-ARN')  # Replace with your Load Balancer ARN
            print("Load Balancer deleted.")
        except elbv2_client.exceptions.LoadBalancerNotFoundException:
            print("No Load Balancer found.")

        # Deleting Auto Scaling Group
        try:
            print("Deleting Auto Scaling Group...")
            autoscaling_client.delete_auto_scaling_group(AutoScalingGroupName='Aditya-ASG', ForceDelete=True)
            print("Auto Scaling Group deleted.")
        except ClientError as e:
            print(f'Error deleting Auto Scaling Group: {e}')

        # Terminating EC2 instances
        print("Terminating EC2 instances...")
        instances = ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['Aditya-EC2-Instance-*']}])
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                ec2_client.terminate_instances(InstanceIds=[instance['InstanceId']])
                print(f'Terminating instance {instance["InstanceId"]}...')
        print("All EC2 instances terminated.")

        # Deleting the S3 bucket
        try:
            bucket_name = 'aditya-serverless-bucket'  # Replace with your S3 bucket name
            print(f'Deleting S3 bucket {bucket_name}...')
            s3_client.delete_bucket(Bucket=bucket_name)
            print(f'S3 bucket {bucket_name} deleted.')
        except ClientError as e:
            print(f'Error deleting S3 bucket: {e}')
    
    except Exception as e:
        print(f'Error during teardown: {e}')

# Main menu for command line interaction
def main_menu():
    print("Welcome to the AWS Infrastructure Setup")
    while True:
        print("\nPlease select an option:")
        print("1. Create S3 Bucket and Upload Static File")
        print("2. Launch EC2 Instances")
        print("3. Create Load Balancer")
        print("4. Create Auto Scaling Group")
        print("5. Set Up SNS Notifications")
        print("6. Tear Down Infrastructure")
        print("7. Exit")
        choice = input("Enter your choice: ")
        
        if choice == '1':
            bucket_name = input("Enter S3 bucket name: ")
            file_path = input("Enter the path of the static file to upload: ")
            file_name = os.path.basename(file_path)
            if not check_s3_bucket_exists(bucket_name):
                create_s3_bucket(bucket_name)
            upload_static_file_to_s3(bucket_name, file_path, file_name)
        
        elif choice == '2':
            bucket_name = input("Enter S3 bucket name: ")
            file_name = input("Enter the static file name: ")
            instance_count = int(input("Enter the number of EC2 instances to launch: "))
            launch_ec2_instances(bucket_name, file_name, instance_count)
        
        elif choice == '3':
            instances = ec2_client.instances.all()  # Fetch all instances
            dns_name = create_load_balancer(instances)
            if dns_name:
                print(f'Load Balancer DNS Name: {dns_name}')
        
        elif choice == '4':
            instance_ids = [instance.id for instance in ec2_client.instances.all()]
            create_auto_scaling_group(instance_ids)
        
        elif choice == '5':
            setup_sns_notifications()
        
        elif choice == '6':
            tear_down()
        
        elif choice == '7':
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
