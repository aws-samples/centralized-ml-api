# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_applicationautoscaling as appscaling,
    Stack,
)
from scripts.utils import get_model_info, camel_to_kebab


class SagemakerModelEndpoint(Construct):
    """
    Constructs and deploys an Amazon SageMaker model endpoint using the AWS Cloud Development Kit (CDK).

    Attributes:
        endpoint_name (str): The name of the deployed SageMaker endpoint.
        model_id (str): The unique identifier for the model.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        model_id: str,
        instance_type: str,
        sagemaker_role: iam.Role,
        model_environment=None,
        model_package_name=None,
        max_capacity=1,
        min_capacity=1,
        invocations_per_instance=5,
        **kwargs,
    ) -> None:
        """
        Initialize the SagemakerModelEndpoint construct.

        Parameters:
            scope (Construct): The parent construct.
            id (str): Unique identifier for the construct.
            model_id (str): Unique identifier for the model.
            instance_type (str): AWS EC2 instance type for inference (e.g., 'ml.g5.xlarge').
            sagemaker_role (iam.Role): IAM Role to be assumed by the SageMaker service.
            model_environment (dict, optional): Environment variables for the SageMaker model. Defaults to None.
            model_package_name (str, optional): The model package name for pre-packaged models. Defaults to None.
            max_capacity (int, optional): The maximum number of instances behind an endpoint.
            min_capacity (int, optional): The minimum number of instances behind an endpoint.
            **kwargs: Additional arguments.
        """

        super().__init__(scope, id)

        # If a model package name is provided, construct the SageMaker model using it
        if model_package_name:
            model = sagemaker.CfnModel(
                self,
                f"Model",
                containers=[
                    sagemaker.CfnModel.ContainerDefinitionProperty(
                        model_package_name=model_package_name,
                        environment=model_environment,
                    )
                ],
                execution_role_arn=sagemaker_role.role_arn,
                model_name=id,
                enable_network_isolation=True,
            )
        else:
            # If no model package name is provided, use custom scripts to fetch model info
            self._model_id = model_id

            MODEL_INFO = get_model_info(
                model_id,
                instance_type,
                region_name=Stack.of(self).region,
            )

            # Log the model information for debugging purposes
            print(f"MODEL_INFO: {MODEL_INFO}")

            model_docker_image = MODEL_INFO["model_docker_image"]
            model_data_url = f"s3://{MODEL_INFO['model_bucket_name']}/{MODEL_INFO['model_bucket_key']}"

            model = sagemaker.CfnModel(
                self,
                f"Model",
                containers=[
                    sagemaker.CfnModel.ContainerDefinitionProperty(
                        image=model_docker_image,
                        model_data_url=model_data_url,
                        environment=model_environment,
                    )
                ],
                execution_role_arn=sagemaker_role.role_arn,
                model_name=id,
            )

        # Configure the endpoint using the constructed model
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            f"EndpointConfig",
            endpoint_config_name=f"{id}-config",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    initial_variant_weight=1,
                    instance_type=instance_type,
                    model_name=model.attr_model_name,
                    initial_instance_count=1,
                )
            ],
        )        

        # Deploy the SageMaker endpoint using the configured endpoint
        self.endpoint = sagemaker.CfnEndpoint(
            self,
            f"Endpoint",
            endpoint_name=f"{camel_to_kebab(id)}-endpoint",
            endpoint_config_name=endpoint_config.attr_endpoint_config_name,
        )

        # Add autoscaling to endpoint
        target = appscaling.ScalableTarget(
            self,
            "ScalableTarget",
            max_capacity=max_capacity,
            min_capacity=min_capacity,
            resource_id=f'endpoint/{self.endpoint.attr_endpoint_name}/variant/AllTraffic',
            scalable_dimension="sagemaker:variant:DesiredInstanceCount",
            service_namespace=appscaling.ServiceNamespace.SAGEMAKER,
        )

        target.scale_to_track_metric(
            "InvocationsPerInstance",
            target_value=invocations_per_instance,
            predefined_metric=appscaling.PredefinedMetric.SAGEMAKER_VARIANT_INVOCATIONS_PER_INSTANCE,
        )

    @property
    def endpoint_name(self) -> str:
        """Returns the name of the deployed SageMaker endpoint."""
        return self.endpoint.attr_endpoint_name

    @property
    def model_id(self) -> str:
        """Returns the unique identifier for the model."""
        return self._model_id
