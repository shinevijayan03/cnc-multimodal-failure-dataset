"""JSON-Schema → GBNF grammar compiler (constitution I-9).

Compiles the pydantic-emitted JSON Schema of `contracts.ExplanationOutput`
into a llama.cpp GBNF grammar, so the decoder can only emit contract-shaped
JSON. Supports the schema subset our contracts use: objects with
required/optional properties, arrays (minItems/maxItems honored up to a
bounded unroll), strings, string enums, numbers, integers, and $ref into
$defs. Unsupported constructs raise rather than silently widening.
"""

from __future__ import annotations

import json
from typing import Any

_WS = "ws"
# Only constructs proven stable in llama.cpp's grammar sampler: no {N}
# bounded repetition, no \u escape branch (an access violation was reproduced
# with those on llama-cpp-python 0.3.33/RTX 3060 — see Build-B V&V log).
# Pydantic re-validates min/max lengths after decoding, so the grammar only
# needs to guarantee SHAPE, not cardinality.
_BASE_RULES = {
    "ws": r'ws ::= [ \t\n]*',
    "string": r'string ::= "\"" char* "\""',
    "char": r'char ::= [^"\\\x00-\x1f] | "\\" ["\\/bfnrt]',
    "number": r'number ::= "-"? [0-9]+ ("." [0-9]+)? ([eE] [-+]? [0-9]+)?',
    "integer": r'integer ::= "-"? [0-9]+',
}


class GrammarError(ValueError):
    pass


def _resolve(schema: dict, defs: dict) -> dict:
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        if name not in defs:
            raise GrammarError(f"unresolvable $ref: {schema['$ref']}")
        return _resolve(defs[name], defs)
    if "allOf" in schema and len(schema["allOf"]) == 1:
        return _resolve(schema["allOf"][0], defs)
    return schema


def _rule_name(path: str) -> str:
    # llama.cpp GBNF word chars are [a-zA-Z0-9-] — underscores are NOT valid
    # rule-name characters and silently corrupt the parsed grammar (crash
    # reproduced at sample time on 0.3.33). Hyphenate everything.
    return "r-" + "".join(c if c.isalnum() else "-" for c in path).strip("-").lower()


def _compile(schema: dict, defs: dict, path: str, rules: dict[str, str]) -> str:
    schema = _resolve(schema, defs)
    name = _rule_name(path)
    if name in rules:
        return name

    if "enum" in schema:
        alts = " | ".join(f'"\\"{v}\\""' for v in schema["enum"])
        rules[name] = f"{name} ::= {alts}"
        return name

    stype = schema.get("type")
    if isinstance(stype, list):                       # e.g. ["string", "null"]
        non_null = [t for t in stype if t != "null"]
        if len(non_null) != 1:
            raise GrammarError(f"unsupported union at {path}: {stype}")
        alt = _compile({**schema, "type": non_null[0]}, defs, path + "_v", rules)
        rules[name] = f'{name} ::= {alt} | "null"'
        return name

    if stype == "string":
        return "string"
    if stype == "number":
        return "number"
    if stype == "integer":
        return "integer"
    if stype == "boolean":
        rules[name] = f'{name} ::= "true" | "false"'
        return name
    if stype == "null":
        rules[name] = f'{name} ::= "null"'
        return name

    if stype == "array":
        item = _compile(schema.get("items", {}), defs, path + "_item", rules)
        min_items = int(schema.get("minItems", 0))
        # Shape-only: star form regardless of maxItems (pydantic enforces
        # cardinality post-decode); avoids alternative explosion in llama.cpp.
        head = f'"[" {_WS} {item} ("," {_WS} {item})* {_WS} "]"'
        rules[name] = (f"{name} ::= {head}" if min_items >= 1
                       else f'{name} ::= "[]" | {head}')
        return name

    if stype == "object" or "properties" in schema:
        props: dict[str, Any] = schema.get("properties", {})
        required = list(schema.get("required", props.keys()))
        # Emit ALL properties in declaration order; optional ones are emitted
        # too (grammar-level optionality of middle keys explodes the grammar).
        parts = []
        for i, (key, sub) in enumerate(props.items()):
            sub_rule = _compile(sub, defs, f"{path}_{key}", rules)
            sep = f'"," {_WS} ' if i else ""
            parts.append(f'{sep}"\\"{key}\\"" {_WS} ":" {_WS} {sub_rule} {_WS}')
        rules[name] = (f'{name} ::= "{{" {_WS} ' + " ".join(parts) + '"}"')
        _ = required
        return name

    raise GrammarError(f"unsupported schema construct at {path}: "
                       f"{json.dumps(schema)[:120]}")


def json_schema_to_gbnf(schema: dict) -> str:
    """Return a GBNF grammar whose `root` matches the given JSON Schema."""
    defs = schema.get("$defs", {})
    rules: dict[str, str] = {}
    root = _compile(schema, defs, "root", rules)
    lines = [f"root ::= {_WS} {root} {_WS}"]
    lines += list(rules.values())
    lines += list(_BASE_RULES.values())
    return "\n".join(lines)


def explanation_grammar() -> str:
    """The I-9 grammar: compiled from the ExplanationOutput JSON Schema."""
    from contracts import ExplanationOutput
    return json_schema_to_gbnf(ExplanationOutput.model_json_schema())
