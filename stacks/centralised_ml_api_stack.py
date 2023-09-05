# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    CfnOutput,
    Duration,
    Stack,
    Aws,
)
from constructs import Construct
from construct.sagemaker_model_endpoint import SagemakerModelEndpoint


class CentralizedMlApiStack(Stack):
    """
    Represents a Cloud Development Kit (CDK) stack containing resources for
    serving machine learning models using AWS services.

    Attributes:
        - Any standard attributes inherited from `Stack` class.
    """

    def __init__(
        self, scope: Construct, construct_id: str, models_config: dict, **kwargs
    ) -> None:
        """
        Initializes the CentralizedMlApiStack CDK stack, iterates through the passed
        in config and deploys the necessary models and endpoints defined

        Parameters:
            scope (Construct): The scope in which this stack is defined.
            construct_id (str): The unique ID for this stack.
            models_config (dict): Configuration details for the models
                                  and endpoints to be created.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(scope, construct_id, **kwargs)

        # ---------------------------------------------------------------------------- #
        #                                      API                                     #
        # ---------------------------------------------------------------------------- #

        # API Gateway Rest API
        api = apigateway.RestApi(
            self,
            "MyApi",
            rest_api_name="ModelService",
            description="This service serves all the sagemaker endpoints either directly or through lambda integrations.",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                # Below could be replaced with the default header list and iterating all the model headers
                allow_headers=["*"],
            ),
        )

        # Create IAM Role for API Gateway with necessary permissions
        api_gateway_role = iam.Role(
            self,
            "ApiGatewayRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

        # Provide ApiGW permissions to invoke the endpoints
        api_gateway_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:InvokeEndpoint"],
                resources=[
                    f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:endpoint/{item['name']}*"
                    for key in models_config
                    for item in models_config[key]
                ],
            )
        )

        # ---------------------------------------------------------------------------- #
        #                             Models and Endpoints                             #
        # ---------------------------------------------------------------------------- #

        model_endpoint_names = []

        # Create an IAM role with Sagemaker permissions
        sagemaker_role = iam.Role(
            self,
            "SagemakerRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
            ],
        )

        # Add custom permissions to the IAM role
        policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudwatch:PutMetricData",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:CreateLogGroup",
                "logs:DescribeLogStreams",
                "s3:GetObject",
                "s3:ListBucket",
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
            ],
            resources=["*"],  # This is permissive, scope this down for production use
        )
        sagemaker_role.add_to_policy(policy_statement)

        # ---------------------------------------------------------------------------- #
        #                           Generated Model Endpoints                          #
        # ---------------------------------------------------------------------------- #

        # This section will deploy SageMaker Model Endpoints and then create an aws integration
        # on the ApiGW to connect to it. If the endpoint is existing it will just create the
        # integration for it.
        for type, models in models_config.items():
            for model in models:
                if type == "models":
                    # Deploys the model to SageMaker. If model_package_arn is provided it will
                    # be used to deploy instead of looking up the model assets from SageMaker
                    modelEndpoint = SagemakerModelEndpoint(
                        self,
                        id=model["name"],
                        model_id=model.get("model_id", None),
                        instance_type=model["instance"],
                        sagemaker_role=sagemaker_role,
                        output_format="text",
                        model_package_name=model.get("model_package_arn", None),
                        **model.get("autoscaling", {}),
                    )
                    model_endpoint_name = modelEndpoint.endpoint_name
                elif type == "endpoints":
                    # Existing endpoint, no need to deploy
                    model_endpoint_name = model["name"]

                model_endpoint_names.append(model_endpoint_name)

                api_resource = api.root.add_resource(model["name"])

                # There are two types of integrations for the model between ApiGW and the SageMaker
                # endpoint, they can either be "api" or "lambda". The "api" type creates a aws
                # integration and passes through the request. A "lambda" integration will invoke
                # the provided lambda function between the ApiGW and the model endpoint.
                if model["integration"]["type"] == "api":
                    # ------------------------- Direct ApiGW Integration ------------------------- #

                    # This creates our integration between ApiGW and the SageMaker Model Endpoint
                    # It will pass through the whole request to the endpoint, as well as the defined
                    # headers. On error it will extract the message from the endpoint response.
                    integration = apigateway.AwsIntegration(
                        service="runtime.sagemaker",
                        integration_http_method="POST",
                        path=f"endpoints/{model_endpoint_name}/invocations",
                        options=apigateway.IntegrationOptions(
                            request_parameters={
                                "integration.request.header.Content-Type": "method.request.header.Content-Type",
                                "integration.request.header.Accept": "method.request.header.Accept",
                                **{
                                    f"integration.request.header.{h}": f"method.request.header.{h}"
                                    for h in model["integration"].get("headers", [])
                                },
                            },
                            credentials_role=api_gateway_role,
                            integration_responses=[
                                apigateway.IntegrationResponse(
                                    status_code="200",
                                    response_templates={
                                        "application/json": "$input.json('$')"
                                    },
                                ),
                                apigateway.IntegrationResponse(
                                    status_code="400",
                                    selection_pattern="4\d{2}",
                                    response_templates={
                                        "application/json": '{ "error": $input.path("$.OriginalMessage") }'
                                    },
                                ),
                                apigateway.IntegrationResponse(
                                    status_code="500",
                                    selection_pattern="5\d{2}",
                                    response_templates={
                                        "application/json": '{ "error": $input.path("$.OriginalMessage") }'
                                    },
                                ),
                            ],
                        ),
                    )

                    # Add the method to our api gateway, includes the headers and error codes.
                    api_resource.add_method(
                        "POST",
                        integration,
                        request_parameters={
                            "method.request.header.Content-Type": True,
                            "method.request.header.Accept": True,
                            **{
                                f"method.request.header.{h}": True
                                for h in model["integration"].get("headers", [])
                            },
                        },
                        method_responses=[
                            apigateway.MethodResponse(status_code="200"),
                            apigateway.MethodResponse(
                                status_code="400",
                                response_models={
                                    "application/json": apigateway.Model.ERROR_MODEL
                                },
                            ),
                            apigateway.MethodResponse(
                                status_code="500",
                                response_models={
                                    "application/json": apigateway.Model.ERROR_MODEL
                                },
                            ),
                        ],
                    )

                # Lambda based integration between ApiGW and the model endpoint
                elif model["integration"]["type"] == "lambda":
                    # ---------------------------- Lambda Integration ---------------------------- #

                    integration_props = model["integration"]["properties"]

                    # Defines custom role for the AWS Lambda functions
                    role_lambda_custom = iam.Role(
                        self,
                        f'RoleLambda${model["name"]}',
                        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                    )

                    role_lambda_custom.add_managed_policy(
                        iam.ManagedPolicy.from_aws_managed_policy_name(
                            "service-role/AWSLambdaBasicExecutionRole"
                        )
                    )

                    # Allows custom permissions to be passed in
                    custom_permissions = integration_props.get("permissions", [])

                    if custom_permissions:
                        role_lambda_custom.attach_inline_policy(
                            iam.Policy(
                                self,
                                f'PolicyInvoke${model["name"]}',
                                statements=[
                                    iam.PolicyStatement(
                                        effect=iam.Effect.ALLOW,
                                        actions=custom_permissions,
                                        resources=[
                                            "*"  # Ideally this would be scoped to specific resources
                                        ],
                                    )
                                ],
                            )
                        )

                    # Add in the integration lambda function
                    lambda_func = _lambda.Function(
                        self,
                        f'LambdaFuncModel${model["name"]}',
                        code=_lambda.Code.from_asset(integration_props["code"]),
                        runtime=_lambda.Runtime(
                            integration_props.get("runtime", "python3.9")
                        ),
                        handler="index.lambda_handler",
                        timeout=Duration.seconds(integration_props.get("timeout", 29)),
                        memory_size=integration_props.get("memory", 128),
                        layers=[
                            _lambda.LayerVersion.from_layer_version_arn(
                                self, f'Layer${model["name"]}{i.split(":")[-2]}', i
                            )
                            for i in integration_props.get("layers", [])
                        ],
                        role=role_lambda_custom,
                        environment={
                            **integration_props.get("environment", {}),
                            "ENDPOINT_NAME": model_endpoint_name,
                        },
                    )

                    # Define the API Gateway resource and method
                    api_resource.add_method(
                        "POST", apigateway.LambdaIntegration(lambda_func)
                    )
