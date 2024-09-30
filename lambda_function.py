import boto3

# Initialize SNS client
sns_client = boto3.client('sns')

def send_sns_notification(topic_arn, subject, message):
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        print(f'SNS Notification sent: {response["MessageId"]}')
    except Exception as e:
        print(f'Error sending SNS notification: {e}')

# Example Lambda function for handling EC2 health check failure
def lambda_handler(event, context):
    try:
        # Extract the event details
        event_type = event['detail']['eventType']

        # Based on event type, send notification to appropriate SNS topic
        if event_type == 'EC2 Instance Health Check Failed':
            send_sns_notification(HEALTH_ISSUE_TOPIC_ARN, 'EC2 Health Issue', 'One of your EC2 instances failed health check.')
        elif event_type == 'EC2 Instance Scaling':
            send_sns_notification(SCALING_EVENT_TOPIC_ARN, 'Scaling Event', 'Auto Scaling triggered an EC2 instance scaling event.')
        elif event_type == 'High Traffic':
            send_sns_notification(HIGH_TRAFFIC_TOPIC_ARN, 'High Traffic', 'High traffic detected on your application.')

    except Exception as e:
        print(f'Error processing event: {e}')
