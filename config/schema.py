# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "models": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                    "model_id": {"type": "string"},
                    "model_package_arn": {"type": "string"},
                    "instance": {"type": "string"},
                    "autoscaling": {
                        "type": "object",
                        "properties": {
                            "max_capacity": {"type": "integer"},
                            "min_capacity": {"type": "integer"},
                            "invocations_per_instance": {"type": "integer"},
                        },
                        "required": [
                            "max_capacity",
                            "min_capacity",
                            "invocations_per_instance",
                        ],
                    },
                    "integration": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["api", "lambda"]},
                            "headers": {"type": "array", "items": {"type": "string"}},
                            "properties": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"},
                                    "permissions": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "timeout": {"type": "integer"},
                                    "memory": {"type": "integer"},
                                    "layers": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "runtime": {"type": "string"},
                                },
                                "required": ["code", "permissions", "timeout"],
                            },
                        },
                        "required": ["type"],
                        "if": {"properties": {"type": {"const": "lambda"}}},
                        "then": {"required": ["properties"]},
                    },
                },
                "anyOf": [
                    {
                        "required": ["model_id"],
                        "not": {"required": ["model_package_arn"]}
                    },
                    {
                        "required": ["model_package_arn"],
                        "not": {"required": ["model_id"]}
                    }
                ],
                "required": ["name", "instance", "integration"],
            },
        },
        "endpoints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                    "integration": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["api", "lambda"]},
                            "headers": {"type": "array", "items": {"type": "string"}},
                            "properties": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"},
                                    "permissions": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "timeout": {"type": "integer"},
                                    "memory": {"type": "integer"},
                                    "layers": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "runtime": {"type": "string"},
                                },
                                "required": ["code", "permissions", "timeout"],
                            },
                        },
                        "required": ["type"],
                        "if": {"properties": {"type": {"const": "lambda"}}},
                        "then": {"required": ["properties"]},
                    },
                },
                "required": ["name", "integration"],
            },
        },
    },
    "required": ["models"],
}
