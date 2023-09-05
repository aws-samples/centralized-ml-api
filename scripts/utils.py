# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from sagemaker import image_uris, model_uris


def get_model_info(model_id, instance_type, region_name):
    """
    Retrieves and returns information about a machine learning model.

    Parameters:
        model_id (str): Unique identifier for the model.
        instance_type (str): AWS EC2 instance type for inference (e.g. 'ml.g5.xlarge').
        region_name (str): AWS region where the model is deployed (e.g. 'us-east-1').

    Returns:
        dict: Dictionary with keys:
            - model_bucket_name (str): S3 bucket containing the model.
            - model_bucket_key (str): S3 bucket path to the model.
            - model_docker_image (str): Docker image URI for inference.
            - instance_type (str): AWS EC2 instance type.
            - region_name (str): AWS region name.
    """
    
    # Constants
    MODEL_VERSION = "*"  # Indicates latest version
    SCOPE = "inference"  # Define the retrieval scope

    # Print input parameters for debugging or logging purposes
    print(model_id, instance_type, region_name)

    # Get the image URI for inference using the given model ID and region
    inference_image_uri = image_uris.retrieve(
        region=region_name,
        framework=None,
        model_id=model_id,
        model_version=MODEL_VERSION,
        image_scope=SCOPE,
        instance_type=instance_type,
    )

    # Get the model URI for inference
    inference_model_uri = model_uris.retrieve(
        model_id=model_id, model_version=MODEL_VERSION, model_scope=SCOPE, region=region_name
    )

    # Extract S3 bucket name and key from the model URI
    model_bucket_name = inference_model_uri.split("/")[2]
    model_bucket_key = "/".join(inference_model_uri.split("/")[3:])
    model_docker_image = inference_image_uri

    # Print the retrieved model URI for debugging or logging purposes
    print(inference_model_uri)

    return {
        "model_bucket_name": model_bucket_name,
        "model_bucket_key": model_bucket_key,
        "model_docker_image": model_docker_image,
        "instance_type": instance_type,
        "region_name": region_name,
    }

def camel_to_kebab(s):
    """
    Converts a camelCase string to a kebab-case string.

    Parameters:
        s (str): Input string in camelCase format.

    Returns:
        str: Converted string in kebab-case format.
    """
    return ''.join(['-'+c.lower() if c.isupper() else c for c in s]).lstrip('-')