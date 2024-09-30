# AWS Infrastructure Setup Script

## Overview

This system automates the lifecycle management of a web application hosted on EC2 instances. It continuously monitors the application's health and dynamically adjusts resources in response to changes in traffic. Additionally, administrators receive timely notifications about the infrastructure's health and scaling events. All the infratsure deployment that is setting up of AWS EC2 instances, attaching a Load Balancer, creating AWS Auto Scaling groups and finally monitoring the health of the deployed infrastrcuture by setting up AWS SNS topics. All this is deployed using BOTO3, including deployment of infrastructure and tearing down of it too.

## Infrastructure Automation

- Create a single script using `boto3` that:
  - Deploys the entire infrastructure.
  - Updates any component as required.
  - Tears down everything when the application is no longer needed.

## AWS Services to be built
- **EC2**
- **ALB - AWS Load Balancer**
- **ASG - Auto scaling groups**
- **SNS**
- **AWS CLI - on local and EC2 instances**

## Prerequisites

- **Python 3.x**: Ensure you have Python 3 installed.
- **Boto3**: The AWS SDK for Python to interact with AWS services.
- **AWS Account**: Make sure you have an AWS account and necessary permissions to create and manage resources.
- **HTML file**: Make sure you have a random static HTML file which you need to place it along the same path as your boto3 script in VS code.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Aditya-rgb/aws-infrastructure-setup.git
   cd aws-infrastructure-setup
   code . # Opening VS code
   
2. **AWS Configure on local**:
- Opened CMD
- Gave the command
- ```bash
  AWS configure
  aws configure set aws_access_key_id <ACCESS_KEY>
  aws configure set aws_secret_access_key <SECRET_KEY>
  aws configure set region us-west-2
  aws configure set output json
  ```
- Congratulations!! you have successfully integrated AWS CLI in your local system!!
## Deployment and Working of the code

1. **Code Deployment**
```bash
python aws_infrastructure_setup.py
```
2. **Select an Option**

The script will present a menu with the following options:

- **Create S3 Bucket - Upload Static HTML File from local to S3**
- **Launch EC2 Instances - setting up of nginx followed by copying the HTML file from S3 to nginx location i.e /var/www/html**
- **Create Load Balancer**
- **Create Auto Scaling Group**
- **Set Up SNS Notifications**
- **Tear Down Infrastructure**
- **Exit**

    ![Alt Text](/images/automation-menu.JPG)

3. **Functionality**
   
Below are functionalities of the Boto3 code :

- **Check if the S3 bucket exists**: This function checks whether the specified S3 bucket exists and creates it if it does not.
- **Create S3 Bucket**: A function that creates a new S3 bucket in the specified region.
- **Upload Static File to S3**: Uploads a specified static file to the S3 bucket.
- **Launch EC2 Instances**: Creates and configures EC2 instances running Nginx followed by copying the HTML file from S3 to nginx location i.e /var/www/html.
- **Create Load Balancer**: Sets up an Application Load Balancer and registers EC2 instances.
- **Create Auto Scaling Group**: Configures an Auto Scaling Group with specified parameters.
- **Setup SNS Notifications**: Creates SNS topics and subscriptions for various notifications.
- **Publish Messages to SNS**: Sends messages to specified SNS topics.
- **Tear Down Infrastructure**: Cleans up all created resources including EC2 instances, Load Balancers, Auto Scaling Groups, and S3 buckets.

    ![Alt Text](/images/automation-teardown-log-1.JPG)

# Overview of Functions

## Functions Overview

- **`check_s3_bucket_exists(bucket_name)`**
  - Checks if the specified S3 bucket exists.
  - Returns `True` if it exists, `False` otherwise.
  - **Relation:** Used before creating a new bucket to avoid duplication.

- **`create_s3_bucket(bucket_name, region='us-west-2')`**
  - Creates a new S3 bucket with the specified name and region.
  - **Relation:** Called only if `check_s3_bucket_exists` returns `False`.

- **`upload_static_file_to_s3(bucket_name, file_path, file_name)`**
  - Uploads a static file to the specified S3 bucket.
  - **Relation:** Called after creating the bucket (if needed) to upload the file.

- **`launch_ec2_instances(bucket_name, file_name, instance_count)`**
  - Launches specified EC2 instances, installs Nginx, and downloads a static file from S3.
  - **Relation:** Depends on the successful upload of the static file to S3 to fetch the file during instance setup.
 
    ![Alt Text](/images/automation-ec2-vs.JPG)
  - In the image we can see EC2 is being launched along with nginx bein installed and AWS s3 command being given to bring the static file from S3 to nginx location i.e /var/www/html.
  - To achieve all this AWS CLI needed to be confiured inside EC2 using the Access key and secret which is also shown above.

- **`create_load_balancer(instances)`**
  - Creates an Application Load Balancer (ALB) and registers the launched EC2 instances to it.
  - **Relation:** Called after launching EC2 instances to ensure traffic is distributed among them.

    ![Alt Text](/images/automation-LB-VS.JPG)
  - In the image above we needed to make sure a VPC Id is provided along with 2 subnets IDs belonging to different Availability Zones.

- **`create_auto_scaling_group(instance_ids)`**
  - Creates an Auto Scaling Group (ASG) with a specified launch template and scaling policies.
  - **Relation:** Designed to work with EC2 instances and ensures that the application can handle varying loads.

- **`create_sns_topics()`**
  - Creates SNS topics for health issues, scaling events, and high traffic.
  - Returns ARNs for the created topics.
  - **Relation:** Topics are used to publish notifications regarding the health and scaling of the infrastructure.

- **`setup_sns_notifications()`**
  - Sets up subscriptions for SNS topics to receive notifications via email/SMS.
  - **Relation:** Enhances the monitoring of infrastructure by allowing users to receive updates.

- **`publish_to_sns(topic_arn, message)`**
  - Publishes messages to the specified SNS topic.
  - **Relation:** Can be used in combination with other functions (like the Lambda function) to notify users of significant events.

- **`create_lambda_for_notifications()`**
  - Creates a Lambda function that handles SNS notifications related to health, scaling, and traffic.
  - **Relation:** Integrates with SNS to process and respond to notifications, enhancing the observability of the infrastructure.
 
    ![Alt Text](/images/automation-lambda-vs.JPG)
    
  - AWS Lambda function code below
     
    ![Alt Text](/images/automation-lambda-vs-1.JPG)

- **`tear_down()`**
  - Cleans up resources by deleting the load balancer, auto-scaling group, EC2 instances, and S3 bucket.
  - **Relation:** This function ensures that no unnecessary resources are left running, preventing unexpected charges.

    ![Alt Text](/images/automation-teardown-log.JPG)

- **`main_menu()`**
  - Displays a command-line interface for users to interact with the script and choose various options.
  - **Relation:** Serves as the entry point for users to trigger other functions based on their selection.

## Function Relationship Flow

1. **Initialization Phase**
   - The user starts at `main_menu()`, where they can choose an action.
   
2. **S3 Operations**
   - If the user chooses to create a bucket and upload a file:
     - `check_s3_bucket_exists()` → `create_s3_bucket()` (if the bucket does not exist) → `upload_static_file_to_s3()`
   
3. **EC2 Operations**
   - If launching instances is chosen:
     - `launch_ec2_instances()` (which relies on the static file being uploaded).

4. **Load Balancer Setup**
   - After launching EC2 instances, the user can create a load balancer using:
     - `create_load_balancer()` (uses the instances from the previous step).

5. **Scaling Operations**
   - The user can create an auto-scaling group:
     - `create_auto_scaling_group()` (depends on the launch template configured in `launch_ec2_instances()`).

6. **Notification Setup**
   - Users can set up SNS topics and notifications:
     - `create_sns_topics()` → `setup_sns_notifications()`
   
7. **Lambda Integration**
   - If the user wants to create a Lambda function:
     - `create_lambda_for_notifications()` (uses SNS topics created previously).

8. **Teardown Operations**
   - If the user chooses to tear down the infrastructure:
     - `tear_down()` → deletes all resources created during the process.

## Testing

Once the AWS infrastructure is deployed using the provided Boto3 scripts, follow these steps to test the setup:

### 1. Verify EC2 Instances
- **Check EC2 Instance Status**: Ensure that the EC2 instances are running.
  - Go to the [EC2 Dashboard](https://console.aws.amazon.com/ec2).
  - Under **Instances**, confirm the instances are in the `running` state.
  - Alternatively, use the AWS CLI to check instance status:
    ```bash
    aws ec2 describe-instances --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]" --output table
    ```
  - Verify that the instances have public IP addresses (if applicable) and are reachable.

### 2. Verify Load Balancer
- **Check Load Balancer Health**: Ensure the Load Balancer is correctly distributing traffic across EC2 instances.
  - Go to the [Load Balancer Dashboard](https://console.aws.amazon.com/ec2/v2/home#LoadBalancers).
  - Confirm that the Load Balancer status is `active`.
  - Verify that all the target instances are `healthy` under the **Target Groups** section.
  - Alternatively, use the AWS CLI to describe the Load Balancer:
    ```bash
    aws elbv2 describe-load-balancers --names <load-balancer-name>
    ```
    Check the `State` and `DNSName` fields.

### 3. Verify Auto Scaling Group (ASG)
- **Check ASG Activity**: Confirm that the Auto Scaling Group (ASG) is scaling the instances as expected.
  - Go to the [Auto Scaling Dashboard](https://console.aws.amazon.com/ec2autoscaling).
  - Verify the number of desired, minimum, and maximum instances in the group.
  - Check the **Scaling Policies** to ensure scaling is configured correctly.
  - Alternatively, use the AWS CLI to describe the Auto Scaling group:
    ```bash
    aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <asg-name>
    ```

### 4. Test Application Accessibility
- **Test Application via Load Balancer**: Access the deployed application through the Load Balancer's DNS name.
  - Retrieve the DNS name of the Load Balancer:
    ```bash
    aws elbv2 describe-load-balancers --names <load-balancer-name> --query "LoadBalancers[*].DNSName" --output text
    ```
  - Open the DNS name in a browser to ensure the application is reachable and functional.
 
    ![Alt Text](/images/automation-dnsname.JPG)

#### 5. Verify S3 Buckets (if applicable)
- **Check S3 Bucket**: Verify that any S3 buckets created as part of the infrastructure are accessible.
  - Go to the [S3 Dashboard](https://console.aws.amazon.com/s3).
  - Confirm that the bucket exists and has the appropriate files (if any were uploaded).
  - Alternatively, use the AWS CLI to list buckets:
    ```bash
    aws s3 ls
    ```


## Contributing

We welcome contributions! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes with clear messages.
4. Submit a pull request for review.

Make sure to follow the code style guidelines and include proper documentation for any new features.

![Alt Text](/1-Automated-S3-Bucket-Cleanup-Using-AWS-Lambda-and-Boto3/images/SA-cloudfare-log-images-deleted-again.JPG)

## Contact

For any queries, feel free to contact me:

- **Email:** adityavakharia@gmail.com
- **GitHub:** [Aditya-rgb](https://github.com/Aditya-rgb/AWS-INFRA-DEPLOYMENT/tree/main)

You can also open an issue in the repository for questions or suggestions.
