"""Builders for web display."""

from .departure_grouping_calculator import (
    DepartureGroupingCalculator,
    DepartureGroupingCalculatorConfig,
    HeaderDisplaySettings,
    generate_pastel_color_from_text,
)

__all__ = [
    "DepartureGroupingCalculator",
    "DepartureGroupingCalculatorConfig",
    "HeaderDisplaySettings",
    "generate_pastel_color_from_text",
]
