"""A JSONField for DRF to handle serialization/deserialization."""

import json
import typing as ty

import pydantic
from django_pydantic_field.v2.rest_framework.fields import (
    SchemaField as PydanticSchemaField,
)
from rest_framework import exceptions, serializers


class JSONField(serializers.Field):
    """
    A custom field for handling JSON data.
    """

    def to_representation(self, value):
        """
        Convert the JSON string to a Python dictionary for serialization.
        """
        return value

    def to_internal_value(self, data):
        """
        Convert the Python dictionary to a JSON string for deserialization.
        """
        if data is None:
            return None
        return json.dumps(data)


class SchemaField(PydanticSchemaField):
    """
    Custom SchemaField in order to create error messages compatible with
    drf_standardized_errors handler.
    """

    def to_internal_value(self, data: ty.Any):
        try:
            if isinstance(data, (str, bytes)):
                return self.adapter.validate_json(data)
            return self.adapter.validate_python(data)
        except pydantic.ValidationError as exc:
            pydantic_errors = exc.errors(
                include_url=False, include_context=False, include_input=False
            )
            errors = []
            for pydantic_error in pydantic_errors:
                for location in pydantic_error.get("loc"):
                    errors.append({location: pydantic_error.get("msg")})

            raise exceptions.ValidationError(errors, code="invalid") from exc
