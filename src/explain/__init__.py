"""Decoder LLM package (Build-B) — GBNF-constrained failure explanations."""

from src.explain.generate import generate_explanation
from src.explain.providers import build_provider

__all__ = ["generate_explanation", "build_provider"]
