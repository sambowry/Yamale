#!/usr/bin/env python
from .schema import Schema
from .yamale_error import YamaleError


def make_schema(path=None, parser="PyYAML", validators=None, content=None):
    # validators = None means use default.
    # Import readers here so we can get version information in setup.py.
    from . import readers

    main_schema = None

    for p in path:
        raw_schemas = readers.parse_yaml(p, parser, content=content)
        if not raw_schemas:
            raise ValueError("{} is an empty file!".format(p))
        # First path, first document is the base schema
        try:
            if not main_schema:
              main_schema = Schema(raw_schemas[0], p, validators=validators)
            else:
              main_schema.add_include(raw_schemas[0])

            # Additional documents contain Includes.
            for raw_schema in raw_schemas[1:]:
                main_schema.add_include(raw_schema)

        except (TypeError, SyntaxError) as e:
            error = "Schema error in file %s\n" % path[0]
            error += str(e)
            raise SyntaxError(error)

    return main_schema


def make_data(path=None, parser="PyYAML", content=None):
    from . import readers

    raw_data = readers.parse_yaml(path, parser, content=content)
    if len(raw_data) == 0:
        return [({}, path)]
    return [(d, path) for d in raw_data]


def validate(schema, data, strict=True, _raise_error=True):
    results = []
    is_valid = True
    for d, path in data:
        result = schema.validate(d, path, strict)
        results.append(result)
        is_valid = is_valid and result.isValid()
    if _raise_error and not is_valid:
        raise YamaleError(results)
    return results
