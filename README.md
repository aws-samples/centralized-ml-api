
# Centralized Machine Learning API

This is a CDK project that stands up a centralized API for use during Hackathons or any event where you want to provide a range of models behind an easy to use centralized API. The models to deploy/integrate with are provided through a configuration file which allows for easy reuse between events and only requires a limited amount of knowledge to be able to use.

<p align="center">
  <img src="/img/architecture.png" />
</p>


> :warning: This artifact deploys a **public API** resource and should be **deleted** when not in use or a form of **authentication should be added** to the API. You are responsible for the costs associated with deploying this project, it is recommended to **destroy the stack when not in use**.

## JSON Schema for Model and Endpoint Configuration

This JSON schema is used for validating the configuration of various machine learning models to deploy and existing endpoints to adopt into the api. 

### Schema

The root object must have properties named `models` and `endpoints`, which are arrays of model objects and endpoint objects, respectively.


- **models**: (Required) An array of objects that define each model.
    - **name**: (Required) A unique string name for the model following the pattern `^[a-z0-9-]+$`.
    - **model_id** OR **model_package_arn**: One of these fields is required. You can specify either a model_id or a model_package_arn, but not both.
      - **model_id**: A string that represents the unique identifier for a model available [here](https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html).
      - **model_package_arn**: ARN (Amazon Resource Name) of the model package.
    - **instance**: (Required) Instance type or identifier.
    - **autoscaling**: Configuration related to autoscaling.
        - **max_capacity**: (Required) Maximum capacity for autoscaling.
        - **min_capacity**: (Required) Minimum capacity for autoscaling.
        - **invocations_per_instance**: (Required) Number of invocations per instance.
    - **integration**: (Required) Defines how the model integrates with other services.
        - **type**: (Required) Can be either "api" or "lambda".
        - **headers**: List of headers if any to pass through to the model.
        - **properties**: Required properties if integration type is "lambda".
            - **code**: (Required) Code for the lambda function.
            - **permissions**: (Required) Array of permissions required by the lambda.
            - **timeout**: (Required) Timeout value for the lambda function.
            - **memory**: Lambda function memory.
            - **layers**: List of Lambda layers.
            - **runtime**: Runtime environment for Lambda.

- **endpoints**: An array of objects that define the endpoints associated with models.
    - **name**: (Required) A unique string name for the endpoint following the pattern `^[a-z0-9-]+$`.
    - **integration**: (Required) Defines how the endpoint integrates with other services. (Same as the integration in models)

:warning: Depending on the `model_package_arn` you specify you may be required to subscribe to a Marketplace Offering to get access to the model package [**here**](https://aws.amazon.com/marketplace/search/results?FULFILLMENT_OPTION_TYPE=SAGEMAKER_MODEL&filters=FULFILLMENT_OPTION_TYPE). 

### Example

Here's an example of a valid JSON object:

```json
{
    "models": [
        {
            "name": "my-model-1",
            "model_id": "model-123",
            "instance": "ml.g5.4xlarge",
            "autoscaling": {
                "max_capacity": 5,
                "min_capacity": 1,
                "invocations_per_instance": 5
            },
            "integration": {
                "type": "lambda",
                "headers": ["Header1", "Header2"],
                "properties": {
                    "code": "functions/model_function",
                    "permissions": ["s3:GetObject", "s3:ListBucket"],
                    "timeout": 30,
                    "memory": 512,
                    "layers": ["arn:aws:lambda:layer:version"],
                    "runtime": "python3.8"
                }
            }
        },
         {
            "name": "my-model-2",
            "model_package_arn": "arn:aws:sagemaker:us-east-1:<ACCOUNT>:model-package/<MODEL_PACKAGE_ID>",
            "instance": "ml.g5.4xlarge",
            "integration": {
                "type": "api",
            }
        }
    ],
    "endpoints": [
        {
            "name": "esiting-endpoint-1",
            "integration": {
                "type": "api",
                "headers": ["HeaderA", "HeaderB"]
            }
        }
    ]
}
```


**Please make sure the JSON objects that you create comply with this schema to ensure proper validation and handling. Endpoints represent existing model endpoints that can be adopted and integrated as part of your configurations.**

## Setup
> :information_source: To synth or deploy this app it is assumed you have aws credentials in your environment.

This project is set up like a standard Python project.  The initialization process also creates a virtualenv within this project, stored under the `.venv` directory.  To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```bash
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following step to activate your virtualenv:

```bash
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```powershell
.venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies:

```bash
pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code:

```bash
cdk synth
```

To add additional dependencies, for example other CDK libraries, just add them to your `setup.py` file and rerun the `pip install -r requirements.txt` command.

Finally you can deploy the project:

```bash
cdk deploy
```

By default the stack will deploy the [models.json](config/models.json) config file. You can also pass in a custom model config file:

```bash
cdk deploy -c config=config/<YOUR_MODEL_CONFIG>.json
```

## Usage

Once you have deployed the stack you will be able to make requests to your endpoints. The api endpoint will be output from the cdk deploy and look like the following:

```
Outputs:
CentralizedMlApiStack.MyApiEndpoint = https://<YOUR_ID>.execute-api.us-east-1.amazonaws.com/prod/
```

Each of the models you have deployed will be available under a different path matching the name you provided. In the example models.json the following endpoints are deployed

```
/open-llama
/sd-1-0
```

We can test these endpoints by passing in payload that the model expects

```bash
curl -X POST https://<YOUR_ID>.execute-api.us-east-1.amazonaws.com/prod/open-llama -d '{"text_inputs": "What is AWS?"}' 
```
And receive a response:

```json
{"generated_texts": ["\nAWS is a cloud computing platform that allows users to store and process data"]}
```

It will also pass the `Content-Type` and `Accept` headers by default (other headers can be specified in the config), so we can invoke the other deployed endpoint as well with :

```bash
curl -X POST https://<YOUR_ID>.execute-api.us-east-1.amazonaws.com/prod/sd-1-0 -d '{"cfg_scale": 7,"height": 512,"width": 512,"steps": 30,"sampler": "K_DPMPP_2M","text_prompts": [{"text": "A computer in the clouds","weight": 1}]}' -H "Content-Type: application/json" 

```
And receive a response:
```json
{
    "result": "success",
    "artifacts": [
        {
            "seed": 2569563647,
            "base64": "<BASE_64_STRING>",
            "finishReason": "SUCCESS"
        }
    ]
}
```
## Useful commands
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk destroy`     destroy this stack and remove resources from your AWS account



## License

This library is licensed under the [MIT-0](https://github.com/aws/mit-0) license. For more details, please see [LICENSE](LICENSE) file

## Legal disclaimer

Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

