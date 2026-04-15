import boto3


def main():
    topic_arn = input("Enter SNS Topic ARN: ").strip()
    user_provided_url = input("Enter HTTPS webhook endpoint URL: ").strip()

    sns = boto3.client("sns")
    response = sns.subscribe(
        TopicArn=topic_arn,
        Protocol="https",
        Endpoint=user_provided_url,
    )
    print(response)


if __name__ == "__main__":
    main()