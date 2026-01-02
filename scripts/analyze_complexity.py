#!/usr/bin/env python3
"""Static analysis tool to measure code complexity and prioritize refactoring.

Measures:
- Cyclomatic complexity (via radon)
- Maximum nesting level per function
- Function length (lines of code)
- Overall priority score for refactoring
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    print("Warning: radon is not installed. Complexity analysis will be limited.", file=sys.stderr)
    print("Install it with: poetry add --group dev radon", file=sys.stderr)


@dataclass
class FunctionMetrics:
    """Metrics for a single function."""

    file_path: str
    function_name: str
    line_start: int
    line_end: int
    cyclomatic_complexity: int
    max_nesting_level: int
    function_length: int
    maintainability_index: float

    @property
    def priority_score(self) -> float:
        """Calculate priority score for refactoring (higher = more urgent)."""
        # Weight factors:
        # - Nesting violations (max 2 allowed): heavy weight
        # - Complexity: medium weight
        # - Function length: light weight
        nesting_penalty = max(0, (self.max_nesting_level - 2) * 10)
        complexity_penalty = max(0, (self.cyclomatic_complexity - 10) * 2)
        length_penalty = max(0, (self.function_length - 50) * 0.5)

        return nesting_penalty + complexity_penalty + length_penalty


class NestingLevelVisitor(ast.NodeVisitor):
    """AST visitor to measure maximum nesting level in a function."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.max_nesting = 0
        self.current_nesting = 0

    def visit(self, node: ast.AST) -> None:
        """Visit a node and track nesting."""
        # Count nesting for control flow structures
        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncFor,
                ast.AsyncWith,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        ):
            self.current_nesting += 1
            self.max_nesting = max(self.max_nesting, self.current_nesting)
            self.generic_visit(node)
            self.current_nesting -= 1
        else:
            self.generic_visit(node)


def analyze_file(file_path: Path) -> list[FunctionMetrics]:
    """Analyze a Python file and return function metrics."""
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []

    # Parse AST
    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []

    # Get cyclomatic complexity from radon (if available)
    radon_results: list[Any] = []
    if RADON_AVAILABLE:
        try:
            radon_results = cc_visit(source_code)
        except Exception as e:
            print(f"Warning: Radon error for {file_path}: {e}", file=sys.stderr)

    # Get maintainability index (if available)
    mi_score = 0.0
    if RADON_AVAILABLE:
        try:
            mi_result = mi_visit(source_code, multi=True)
            mi_score = mi_result[1] if isinstance(mi_result, tuple) else mi_result
        except Exception:
            pass

    metrics: list[FunctionMetrics] = []

    # Find all function definitions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = node.name
            line_start = node.lineno
            line_end = node.end_lineno if hasattr(node, "end_lineno") else line_start

            # Calculate function length
            function_length = line_end - line_start + 1

            # Measure nesting level
            visitor = NestingLevelVisitor()
            visitor.visit(node)
            max_nesting = visitor.max_nesting

            # Find matching radon result (or estimate complexity)
            cyclomatic_complexity = 1  # Default
            if RADON_AVAILABLE:
                for radon_func in radon_results:
                    if radon_func.name == func_name and radon_func.lineno == line_start:
                        cyclomatic_complexity = radon_func.complexity
                        break
            else:
                # Simple estimation: count control flow nodes
                control_flow_nodes = sum(
                    1
                    for n in ast.walk(node)
                    if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor, ast.AsyncWith))
                )
                cyclomatic_complexity = 1 + control_flow_nodes

            metrics.append(
                FunctionMetrics(
                    file_path=str(file_path),
                    function_name=func_name,
                    line_start=line_start,
                    line_end=line_end,
                    cyclomatic_complexity=cyclomatic_complexity,
                    max_nesting_level=max_nesting,
                    function_length=function_length,
                    maintainability_index=float(mi_score),
                )
            )

    return metrics


def find_python_files(root_dir: Path) -> Iterator[Path]:
    """Find all Python files in the source directory."""
    for path in root_dir.rglob("*.py"):
        # Skip __pycache__ and test files for now (can be included later)
        if "__pycache__" not in str(path) and "test_" not in path.name:
            yield path


def format_priority(score: float) -> str:
    """Format priority score as a string."""
    if score >= 20:
        return "🔴 CRITICAL"
    elif score >= 10:
        return "🟠 HIGH"
    elif score >= 5:
        return "🟡 MEDIUM"
    elif score > 0:
        return "🟢 LOW"
    else:
        return "✅ OK"


def print_priority_table(top_metrics: list[FunctionMetrics], limit: int = 30) -> None:
    """Print top priority functions in a tabular format."""
    if not top_metrics:
        return

    # Get relative paths
    project_root = Path(__file__).parent.parent
    metrics_with_paths = []
    for m in top_metrics[:limit]:
        try:
            rel_path = Path(m.file_path).relative_to(project_root)
        except ValueError:
            rel_path = Path(m.file_path)
        metrics_with_paths.append((rel_path, m))

    # Calculate column widths
    max_file_len = max(len(str(p)) for p, _ in metrics_with_paths) if metrics_with_paths else 0
    max_func_len = max(len(m.function_name) for _, m in metrics_with_paths) if metrics_with_paths else 0
    max_file_len = min(max_file_len, 50)  # Cap at 50 chars
    max_func_len = min(max_func_len, 30)  # Cap at 30 chars

    # Print header with proper spacing
    col_widths = {
        'priority': 12,
        'file': max_file_len + 2,
        'function': max_func_len + 2,
        'lines': 12,
        'nest': 6,
        'complex': 8,
        'length': 8,
    }
    
    header = (
        f"{'Priority':<{col_widths['priority']}} "
        f"{'File':<{col_widths['file']}} "
        f"{'Function':<{col_widths['function']}} "
        f"{'Lines':<{col_widths['lines']}} "
        f"{'Nest':<{col_widths['nest']}} "
        f"{'Complex':<{col_widths['complex']}} "
        f"{'Length':<{col_widths['length']}}"
    )
    separator = "=" * len(header)
    print(f"\n{separator}")
    print(header)
    print(separator)

    # Print rows
    for rel_path, metric in metrics_with_paths:
        file_str = str(rel_path)
        if len(file_str) > max_file_len:
            file_str = "..." + file_str[-(max_file_len - 3):]

        func_str = metric.function_name
        if len(func_str) > max_func_len:
            func_str = func_str[: max_func_len - 3] + "..."

        priority_str = format_priority(metric.priority_score)
        lines_str = f"{metric.line_start}-{metric.line_end}"
        nest_str = f"{metric.max_nesting_level}"
        complex_str = f"{metric.cyclomatic_complexity}"
        length_str = f"{metric.function_length}"

        row = (
            f"{priority_str:<{col_widths['priority']}} "
            f"{file_str:<{col_widths['file']}} "
            f"{func_str:<{col_widths['function']}} "
            f"{lines_str:<{col_widths['lines']}} "
            f"{nest_str:<{col_widths['nest']}} "
            f"{complex_str:<{col_widths['complex']}} "
            f"{length_str:<{col_widths['length']}}"
        )
        print(row)

    print(separator)
    print(f"\nShowing top {min(limit, len(top_metrics))} functions by priority score")
    print("Legend: Nest = Max nesting level, Complex = Cyclomatic complexity, Length = Lines of code")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    else:
        root_dir = Path(__file__).parent.parent / "src" / "mvg_departures"

    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing Python files in: {root_dir}")
    print("=" * 80)

    all_metrics: list[FunctionMetrics] = []

    for py_file in find_python_files(root_dir):
        metrics = analyze_file(py_file)
        all_metrics.extend(metrics)

    # Sort by priority score (descending)
    all_metrics.sort(key=lambda m: m.priority_score, reverse=True)

    # Print summary
    print(f"\nTotal functions analyzed: {len(all_metrics)}")
    print(f"Functions with nesting > 2: {sum(1 for m in all_metrics if m.max_nesting_level > 2)}")
    print(f"Functions with complexity > 10: {sum(1 for m in all_metrics if m.cyclomatic_complexity > 10)}")
    print(f"Functions with length > 50: {sum(1 for m in all_metrics if m.function_length > 50)}")

    # Print top priorities in tabular format
    print("\n" + "=" * 80)
    print("TOP REFACTORING PRIORITIES (TABULAR VIEW)")
    print("=" * 80)

    top_priority_metrics = [m for m in all_metrics if m.priority_score > 0]
    print_priority_table(top_priority_metrics, limit=30)

    # Also show detailed view grouped by file
    print("\n" + "=" * 80)
    print("TOP REFACTORING PRIORITIES (DETAILED VIEW BY FILE)")
    print("=" * 80)

    # Group by file
    file_groups: dict[str, list[FunctionMetrics]] = {}
    for metric in all_metrics:
        if metric.priority_score > 0:
            file_groups.setdefault(metric.file_path, []).append(metric)

    # Sort files by highest priority function
    sorted_files = sorted(
        file_groups.items(),
        key=lambda item: max(m.priority_score for m in item[1]),
        reverse=True,
    )

    for file_path, file_metrics in sorted_files[:20]:  # Top 20 files
        rel_path = Path(file_path).relative_to(Path(__file__).parent.parent)
        max_priority = max(m.priority_score for m in file_metrics)
        print(f"\n{format_priority(max_priority)} {rel_path}")
        print("-" * 80)

        # Show top functions in this file
        for metric in sorted(file_metrics, key=lambda m: m.priority_score, reverse=True)[:5]:
            if metric.priority_score > 0:
                print(
                    f"  Function: {metric.function_name} (lines {metric.line_start}-{metric.line_end})"
                )
                print(f"    Priority: {format_priority(metric.priority_score)} ({metric.priority_score:.1f})")
                print(f"    Nesting: {metric.max_nesting_level} (max 2 allowed)")
                print(f"    Complexity: {metric.cyclomatic_complexity} (recommended < 10)")
                print(f"    Length: {metric.function_length} lines (recommended < 50)")
                print()

    # Generate JSON report
    report_path = Path(__file__).parent.parent / "complexity_report.json"
    report_data = {
        "summary": {
            "total_functions": len(all_metrics),
            "functions_with_nesting_violations": sum(1 for m in all_metrics if m.max_nesting_level > 2),
            "functions_with_high_complexity": sum(1 for m in all_metrics if m.cyclomatic_complexity > 10),
            "functions_with_high_length": sum(1 for m in all_metrics if m.function_length > 50),
        },
        "functions": [
            {
                "file": m.file_path,
                "function": m.function_name,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "cyclomatic_complexity": m.cyclomatic_complexity,
                "max_nesting_level": m.max_nesting_level,
                "function_length": m.function_length,
                "maintainability_index": m.maintainability_index,
                "priority_score": m.priority_score,
            }
            for m in all_metrics
            if m.priority_score > 0
        ],
    }

    with report_path.open("w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()

