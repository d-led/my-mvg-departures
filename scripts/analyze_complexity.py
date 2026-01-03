#!/usr/bin/env python3
"""Static analysis tool to measure code complexity and prioritize refactoring.

Measures:
- Cyclomatic complexity (via radon)
- Maximum nesting level per function
- Function length (lines of code)
- Parameter count (max 4 regular params + *args + **kwargs)
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
    parameter_count: int
    has_varargs: bool
    has_kwargs: bool
    maintainability_index: float
    is_protocol_method: bool = False

    @property
    def parameter_violation(self) -> int:
        """Calculate parameter count violation (0 if OK, positive if too many)."""
        # Max allowed: 4 regular params + *args + **kwargs
        max_allowed = 4
        if self.has_varargs:
            max_allowed += 1
        if self.has_kwargs:
            max_allowed += 1
        return max(0, self.parameter_count - max_allowed)

    @property
    def priority_score(self) -> float:
        """Calculate priority score for refactoring (higher = more urgent)."""
        # Weight factors:
        # - Nesting violations (max 2 allowed): heavy weight
        # - Complexity: medium weight
        # - Function length: light weight
        # - Parameter count: medium weight
        nesting_penalty = max(0, (self.max_nesting_level - 2) * 10)
        complexity_penalty = max(0, (self.cyclomatic_complexity - 10) * 2)
        length_penalty = max(0, (self.function_length - 50) * 0.5)
        parameter_penalty = self.parameter_violation * 3

        return nesting_penalty + complexity_penalty + length_penalty + parameter_penalty


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


def count_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, bool, bool]:
    """Count function parameters.
    
    Returns:
        Tuple of (regular_param_count, has_varargs, has_kwargs)
        Regular params exclude 'self' and 'cls'.
    """
    args = node.args
    regular_count = 0
    has_varargs = args.vararg is not None
    has_kwargs = args.kwarg is not None
    
    # Count regular arguments, excluding 'self' and 'cls'
    for arg in args.args:
        if arg.arg not in ('self', 'cls'):
            regular_count += 1
    
    return regular_count, has_varargs, has_kwargs


def is_protocol_class(node: ast.ClassDef, tree: ast.AST) -> bool:
    """Check if a class is a Protocol class."""
    # Check if class inherits from Protocol
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute):
            # Handle typing.Protocol or typing_extensions.Protocol
            if isinstance(base.value, ast.Name) and base.value.id in ("typing", "typing_extensions"):
                if base.attr == "Protocol":
                    return True
    return False


def get_protocol_base_names(node: ast.ClassDef) -> list[str]:
    """Get names of Protocol classes that this class inherits from."""
    protocol_names = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            protocol_names.append(base.id)
        elif isinstance(base, ast.Attribute):
            # Handle cases like mvg_departures.domain.ports.DepartureRepository
            if isinstance(base.value, ast.Attribute):
                # Nested attribute like domain.ports.DepartureRepository
                protocol_names.append(base.attr)
            elif isinstance(base.value, ast.Name):
                protocol_names.append(base.attr)
    return protocol_names


def find_parent_class(node: ast.AST, tree: ast.AST) -> ast.ClassDef | None:
    """Find the parent class of a node."""
    for class_node in ast.walk(tree):
        if isinstance(class_node, ast.ClassDef):
            for child in ast.walk(class_node):
                if child is node:
                    return class_node
    return None


def is_protocol_file_path(file_path: Path) -> bool:
    """Check if file path suggests it's a protocol/contract file."""
    name_lower = file_path.name.lower()
    return "protocol" in name_lower or "contracts" in name_lower or "ports" in name_lower


def collect_protocol_classes_from_file(
    tree: ast.AST, protocol_signatures: dict[str, set[str]]
) -> set[str]:
    """Collect Protocol classes defined in this file."""
    protocol_classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_protocol_class(node, tree):
            protocol_classes.add(node.name)
            if node.name not in protocol_signatures:
                method_names = {
                    child.name
                    for child in ast.walk(node)
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                protocol_signatures[node.name] = method_names
    return protocol_classes


def find_protocol_implementing_classes(
    tree: ast.AST, protocol_classes: set[str], protocol_signatures: dict[str, set[str]]
) -> set[str]:
    """Find classes that implement protocols."""
    implementing_classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = get_protocol_base_names(node)
            for base_name in base_names:
                if base_name in protocol_classes or base_name in protocol_signatures:
                    implementing_classes.add(node.name)
                    break
    return implementing_classes


def check_if_protocol_method(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    parent_class: ast.ClassDef | None,
    protocol_classes: set[str],
    protocol_implementing_classes: set[str],
    protocol_signatures: dict[str, set[str]],
    is_protocol_file: bool,
) -> bool:
    """Check if a function is a protocol method."""
    if not parent_class:
        return is_protocol_file
    
    if parent_class.name in protocol_classes:
        return True
    
    if parent_class.name in protocol_implementing_classes:
        func_name = func_node.name
        return any(func_name in method_names for method_names in protocol_signatures.values())
    
    return False


def get_cyclomatic_complexity(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    func_name: str,
    line_start: int,
    radon_results: list[Any],
) -> int:
    """Get cyclomatic complexity for a function."""
    if RADON_AVAILABLE:
        for radon_func in radon_results:
            if radon_func.name == func_name and radon_func.lineno == line_start:
                return radon_func.complexity
    
    # Simple estimation: count control flow nodes
    control_flow_types = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncFor,
        ast.AsyncWith,
    )
    control_flow_count = sum(1 for n in ast.walk(func_node) if isinstance(n, control_flow_types))
    return 1 + control_flow_count


def analyze_function_node(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: Path,
    tree: ast.AST,
    protocol_classes: set[str],
    protocol_implementing_classes: set[str],
    protocol_signatures: dict[str, set[str]],
    is_protocol_file: bool,
    radon_results: list[Any],
    mi_score: float,
) -> FunctionMetrics:
    """Analyze a single function node and return metrics."""
    func_name = func_node.name
    line_start = func_node.lineno
    line_end = func_node.end_lineno if hasattr(func_node, "end_lineno") else line_start
    
    parent_class = find_parent_class(func_node, tree)
    is_protocol_method = check_if_protocol_method(
        func_node,
        parent_class,
        protocol_classes,
        protocol_implementing_classes,
        protocol_signatures,
        is_protocol_file,
    )
    
    function_length = line_end - line_start + 1
    
    visitor = NestingLevelVisitor()
    visitor.visit(func_node)
    max_nesting = visitor.max_nesting
    
    param_count, has_varargs, has_kwargs = count_parameters(func_node)
    cyclomatic_complexity = get_cyclomatic_complexity(func_node, func_name, line_start, radon_results)
    
    return FunctionMetrics(
        file_path=str(file_path),
        function_name=func_name,
        line_start=line_start,
        line_end=line_end,
        cyclomatic_complexity=cyclomatic_complexity,
        max_nesting_level=max_nesting,
        function_length=function_length,
        parameter_count=param_count,
        has_varargs=has_varargs,
        has_kwargs=has_kwargs,
        maintainability_index=float(mi_score),
        is_protocol_method=is_protocol_method,
    )


def get_radon_metrics(source_code: str, file_path: Path) -> tuple[list[Any], float]:
    """Get radon metrics if available."""
    radon_results: list[Any] = []
    mi_score = 0.0
    
    if not RADON_AVAILABLE:
        return radon_results, mi_score
    
    try:
        radon_results = cc_visit(source_code)
    except Exception as e:
        print(f"Warning: Radon error for {file_path}: {e}", file=sys.stderr)
    
    try:
        mi_result = mi_visit(source_code, multi=True)
        mi_score = mi_result[1] if isinstance(mi_result, tuple) else mi_result
    except Exception:
        pass
    
    return radon_results, mi_score


def analyze_file(file_path: Path, protocol_signatures: dict[str, set[str]] | None = None) -> list[FunctionMetrics]:
    """Analyze a Python file and return function metrics."""
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []

    if protocol_signatures is None:
        protocol_signatures = {}
    
    is_protocol_file = is_protocol_file_path(file_path)
    protocol_classes = collect_protocol_classes_from_file(tree, protocol_signatures)
    protocol_implementing_classes = find_protocol_implementing_classes(
        tree, protocol_classes, protocol_signatures
    )
    
    radon_results, mi_score = get_radon_metrics(source_code, file_path)
    
    metrics: list[FunctionMetrics] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metric = analyze_function_node(
                node,
                file_path,
                tree,
                protocol_classes,
                protocol_implementing_classes,
                protocol_signatures,
                is_protocol_file,
                radon_results,
                mi_score,
            )
            metrics.append(metric)

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
        'params': 8,
    }
    
    header = (
        f"{'Priority':<{col_widths['priority']}} "
        f"{'File':<{col_widths['file']}} "
        f"{'Function':<{col_widths['function']}} "
        f"{'Lines':<{col_widths['lines']}} "
        f"{'Nest':<{col_widths['nest']}} "
        f"{'Complex':<{col_widths['complex']}} "
        f"{'Length':<{col_widths['length']}} "
        f"{'Params':<{col_widths['params']}}"
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
        # Format params: show count + *args/**kwargs indicators
        param_parts = [str(metric.parameter_count)]
        if metric.has_varargs:
            param_parts.append("*args")
        if metric.has_kwargs:
            param_parts.append("**kwargs")
        params_str = "+".join(param_parts)

        row = (
            f"{priority_str:<{col_widths['priority']}} "
            f"{file_str:<{col_widths['file']}} "
            f"{func_str:<{col_widths['function']}} "
            f"{lines_str:<{col_widths['lines']}} "
            f"{nest_str:<{col_widths['nest']}} "
            f"{complex_str:<{col_widths['complex']}} "
            f"{length_str:<{col_widths['length']}} "
            f"{params_str:<{col_widths['params']}}"
        )
        print(row)

    print(separator)
    print(f"\nShowing top {min(limit, len(top_metrics))} functions by priority score")
    print("Legend: Nest = Max nesting level, Complex = Cyclomatic complexity, Length = Lines of code, Params = Parameter count")


def collect_protocol_signatures(root_dir: Path) -> dict[str, set[str]]:
    """Collect all Protocol class names and their method signatures across all files.
    
    Returns:
        Dictionary mapping protocol class names to sets of method names.
    """
    protocol_signatures: dict[str, set[str]] = {}
    
    for py_file in find_python_files(root_dir):
        try:
            source_code = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source_code, filename=str(py_file))
        except Exception:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if is_protocol_class(node, tree):
                    method_names = set()
                    for child in ast.walk(node):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_names.add(child.name)
                    protocol_signatures[node.name] = method_names
    
    return protocol_signatures


def print_summary(
    all_metrics: list[FunctionMetrics],
    regular_metrics: list[FunctionMetrics],
    protocol_metrics: list[FunctionMetrics],
) -> None:
    """Print summary statistics."""
    regular_param_violations = sum(1 for m in regular_metrics if m.parameter_violation > 0)
    protocol_param_violations = sum(1 for m in protocol_metrics if m.parameter_violation > 0)
    
    print(f"\nTotal functions analyzed: {len(all_metrics)}")
    print(f"  - Regular functions: {len(regular_metrics)}")
    print(f"  - Protocol/interface methods: {len(protocol_metrics)}")
    print(f"Functions with nesting > 2: {sum(1 for m in regular_metrics if m.max_nesting_level > 2)}")
    print(f"Functions with complexity > 10: {sum(1 for m in regular_metrics if m.cyclomatic_complexity > 10)}")
    print(f"Functions with length > 50: {sum(1 for m in regular_metrics if m.function_length > 50)}")
    print(f"Functions with too many parameters: {regular_param_violations} (regular) + {protocol_param_violations} (protocol)")


def print_protocol_methods(protocol_metrics: list[FunctionMetrics], project_root: Path) -> None:
    """Print protocol methods with violations."""
    protocol_with_violations = [m for m in protocol_metrics if m.parameter_violation > 0]
    if not protocol_with_violations:
        return
    
    print("\n" + "=" * 80)
    print("PROTOCOL/INTERFACE METHODS (excluded from refactoring priorities)")
    print("=" * 80)
    
    for m in sorted(protocol_with_violations, key=lambda x: (x.file_path, x.function_name)):
        try:
            rel_path = Path(m.file_path).relative_to(project_root)
        except ValueError:
            rel_path = Path(m.file_path)
        print(f"  {rel_path}::{m.function_name} ({m.parameter_count} params, {m.parameter_violation} over limit)")
    
    print("  Note: Protocol methods maintain interface contracts and cannot be refactored.")


def format_parameter_info(metric: FunctionMetrics) -> tuple[str, int]:
    """Format parameter information string and calculate max allowed."""
    param_info = str(metric.parameter_count)
    if metric.has_varargs:
        param_info += " + *args"
    if metric.has_kwargs:
        param_info += " + **kwargs"
    max_allowed = 4 + (1 if metric.has_varargs else 0) + (1 if metric.has_kwargs else 0)
    return param_info, max_allowed


def print_detailed_file_view(regular_metrics: list[FunctionMetrics], project_root: Path) -> None:
    """Print detailed view grouped by file."""
    file_groups: dict[str, list[FunctionMetrics]] = {}
    for metric in regular_metrics:
        if metric.priority_score > 0:
            file_groups.setdefault(metric.file_path, []).append(metric)
    
    sorted_files = sorted(
        file_groups.items(),
        key=lambda item: max(m.priority_score for m in item[1]),
        reverse=True,
    )
    
    for file_path, file_metrics in sorted_files[:20]:
        rel_path = Path(file_path).relative_to(project_root)
        max_priority = max(m.priority_score for m in file_metrics)
        print(f"\n{format_priority(max_priority)} {rel_path}")
        print("-" * 80)
        
        for metric in sorted(file_metrics, key=lambda m: m.priority_score, reverse=True)[:5]:
            if metric.priority_score > 0:
                print(f"  Function: {metric.function_name} (lines {metric.line_start}-{metric.line_end})")
                print(f"    Priority: {format_priority(metric.priority_score)} ({metric.priority_score:.1f})")
                print(f"    Nesting: {metric.max_nesting_level} (max 2 allowed)")
                print(f"    Complexity: {metric.cyclomatic_complexity} (recommended < 10)")
                print(f"    Length: {metric.function_length} lines (recommended < 50)")
                param_info, max_allowed = format_parameter_info(metric)
                print(f"    Parameters: {param_info} (max {max_allowed} allowed: 4 regular + *args + **kwargs)")
                if metric.parameter_violation > 0:
                    print(f"      ⚠️  {metric.parameter_violation} parameter(s) over limit")
                print()


def generate_json_report(
    all_metrics: list[FunctionMetrics],
    regular_metrics: list[FunctionMetrics],
    protocol_metrics: list[FunctionMetrics],
    report_path: Path,
) -> None:
    """Generate JSON report file."""
    regular_param_violations = sum(1 for m in regular_metrics if m.parameter_violation > 0)
    protocol_param_violations = sum(1 for m in protocol_metrics if m.parameter_violation > 0)
    
    report_data = {
        "summary": {
            "total_functions": len(all_metrics),
            "regular_functions": len(regular_metrics),
            "protocol_methods": len(protocol_metrics),
            "functions_with_nesting_violations": sum(1 for m in regular_metrics if m.max_nesting_level > 2),
            "functions_with_high_complexity": sum(1 for m in regular_metrics if m.cyclomatic_complexity > 10),
            "functions_with_high_length": sum(1 for m in regular_metrics if m.function_length > 50),
            "functions_with_too_many_parameters": regular_param_violations,
            "protocol_methods_with_too_many_parameters": protocol_param_violations,
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
                "parameter_count": m.parameter_count,
                "has_varargs": m.has_varargs,
                "has_kwargs": m.has_kwargs,
                "parameter_violation": m.parameter_violation,
                "maintainability_index": m.maintainability_index,
                "priority_score": m.priority_score,
                "is_protocol_method": m.is_protocol_method,
            }
            for m in all_metrics
            if m.priority_score > 0 or (m.is_protocol_method and m.parameter_violation > 0)
        ],
    }
    
    with report_path.open("w") as f:
        json.dump(report_data, f, indent=2)


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

    print("Collecting protocol signatures...")
    protocol_signatures = collect_protocol_signatures(root_dir)

    all_metrics: list[FunctionMetrics] = []
    for py_file in find_python_files(root_dir):
        metrics = analyze_file(py_file, protocol_signatures)
        all_metrics.extend(metrics)

    all_metrics.sort(key=lambda m: m.priority_score, reverse=True)

    protocol_metrics = [m for m in all_metrics if m.is_protocol_method]
    regular_metrics = [m for m in all_metrics if not m.is_protocol_method]

    print_summary(all_metrics, regular_metrics, protocol_metrics)

    project_root = Path(__file__).parent.parent
    print_protocol_methods(protocol_metrics, project_root)

    print("\n" + "=" * 80)
    print("TOP REFACTORING PRIORITIES (TABULAR VIEW)")
    print("=" * 80)
    top_priority_metrics = [m for m in regular_metrics if m.priority_score > 0]
    print_priority_table(top_priority_metrics, limit=30)

    print("\n" + "=" * 80)
    print("TOP REFACTORING PRIORITIES (DETAILED VIEW BY FILE)")
    print("=" * 80)
    print_detailed_file_view(regular_metrics, project_root)

    report_path = project_root / "complexity_report.json"
    generate_json_report(all_metrics, regular_metrics, protocol_metrics, report_path)
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()

