# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Envvars
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')

# Clients for reuse
sagemaker_client = boto3.client("runtime.sagemaker")


def return_error(err):
    """Parses error message and returns a formatted response

    :param err: Exception error
    :returns: dict
    """
    return {
        "statusCode": err.response["ResponseMetadata"]["HTTPStatusCode"],
        "body": json.dumps(
            f'{err.response["Error"]["Code"]}: {err.response["Error"]["Message"]}'
        ),
        "headers": {"content-type": "application/json"},
    }


def sync_invoke(
    payload, endpoint_name, content_type, accept):
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType=content_type,
            Accept=accept,
        )

        response_body = json.loads(response["Body"].read().decode())

    except ClientError as e:
        logger.error(e)
        return return_error(e)
    return {
        "statusCode": 200,
        "body": json.dumps(response_body),
        "headers": {"Content-Type": "application/json"},
    }


def lambda_handler(event, context):
    """Accepts an event from api gateway for model invocation

    :returns: model output
    """
    payload = json.loads(event["body"])

    # path name matches endpoint name with a leading slash
    endpoint_name = event["path"][1::] + "-endpoint"
    content_type = event["headers"].get("Content-Type","application/json")
    accept = event["headers"].get("Accept", "application/json")

    return sync_invoke(payload, ENDPOINT_NAME, content_type, accept)
