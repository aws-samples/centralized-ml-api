#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import aws_cdk as cdk
from jsonschema import validate, exceptions

from stacks.centralised_ml_api_stack import CentralizedMlApiStack
from config.schema import schema

# Creating the app first allows the context to be pulled to retrieve the passed in model config
app = cdk.App()

config_path = app.node.try_get_context("config") or "config/models.json"

print(f'Loading Config File: {config_path}')

# Load the schema
with open(config_path, "r") as file:
    config = json.load(file)

# Validate the data
try:
    validate(instance=config, schema=schema)
    print("JSON data is valid.")
except exceptions.ValidationError as e:
    print(f"JSON data is invalid. Error: {e}")
    exit(1) # Exit early on invalid config

# The model id's and packages need to resolve to a specific region at deploy time so we set this 
# value to be passed into the stack. You can change this value yourself but make sure any 
# resource that references a region matches the region set here.
env = cdk.Environment(region="us-east-1")

centralised_ml_api_stack = CentralizedMlApiStack(
    app,
    "CentralizedMlApiStack",
    models_config=config,
    env=env
)

app.synth()
