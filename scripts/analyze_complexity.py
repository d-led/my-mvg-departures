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
    print("Install it with: poetry install --with dev", file=sys.stderr)


@dataclass(frozen=True)
class ProtocolContext:
    """Context information about protocols in a file."""

    protocol_classes: set[str]
    protocol_implementing_classes: set[str]
    protocol_signatures: dict[str, set[str]]
    is_protocol_file: bool


@dataclass(frozen=True)
class AnalysisContext:
    """Context for analysis tools (radon, etc.)."""

    radon_results: list[Any]
    mi_score: float


@dataclass(frozen=True)
class FileAnalysisContext:
    """Complete context for analyzing a file."""

    file_path: Path
    tree: ast.AST
    protocol_context: ProtocolContext
    analysis_context: AnalysisContext


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

    def _calculate_nesting_penalty(self) -> float:
        """Calculate penalty for nesting violations."""
        return max(0, (self.max_nesting_level - 2) * 10)

    def _calculate_complexity_penalty(self) -> float:
        """Calculate penalty for complexity violations."""
        return max(0, (self.cyclomatic_complexity - 10) * 2)

    def _calculate_length_penalty(self) -> float:
        """Calculate penalty for function length violations."""
        return max(0, (self.function_length - 50) * 0.5)

    def _calculate_parameter_penalty(self) -> float:
        """Calculate penalty for parameter count violations."""
        return self.parameter_violation * 3

    def _calculate_mi_penalty(self) -> float:
        """Calculate penalty based on Maintainability Index.
        
        MI ranges from 0-100:
        - 20-100: Maintainable (no penalty)
        - 10-19: Difficult to maintain (penalty 2.5-5)
        - 0-9: Very difficult to maintain (penalty 5.5-10)
        - 0 or unavailable: Default penalty 2.5
        """
        if self.maintainability_index <= 0:
            return 2.5
        if self.maintainability_index < 10:
            return 10 - (self.maintainability_index * 0.5)
        if self.maintainability_index < 20:
            return 5 - ((self.maintainability_index - 10) * 0.25)
        return 0.0

    @property
    def priority_score(self) -> float:
        """Calculate priority score for refactoring (higher = more urgent).
        
        Combines penalties from:
        - Nesting violations (max 2 allowed): heavy weight
        - Complexity: medium weight
        - Function length: light weight
        - Parameter count: medium weight
        - Maintainability Index: medium weight (lower MI = higher penalty)
        """
        return (
            self._calculate_nesting_penalty()
            + self._calculate_complexity_penalty()
            + self._calculate_length_penalty()
            + self._calculate_parameter_penalty()
            + self._calculate_mi_penalty()
        )


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


def _is_simple_protocol_base(base: ast.AST) -> bool:
    """Check if base is a simple Protocol name."""
    return isinstance(base, ast.Name) and base.id == "Protocol"


def _is_qualified_protocol_base(base: ast.AST) -> bool:
    """Check if base is a qualified Protocol (typing.Protocol)."""
    if not isinstance(base, ast.Attribute):
        return False
    if base.attr != "Protocol":
        return False
    if not isinstance(base.value, ast.Name):
        return False
    return base.value.id in ("typing", "typing_extensions")


def is_protocol_class(node: ast.ClassDef, tree: ast.AST) -> bool:
    """Check if a class is a Protocol class."""
    for base in node.bases:
        if _is_simple_protocol_base(base) or _is_qualified_protocol_base(base):
            return True
    return False


def _extract_name_from_base(base: ast.AST) -> str | None:
    """Extract class name from a base class AST node."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def get_protocol_base_names(node: ast.ClassDef) -> list[str]:
    """Get names of Protocol classes that this class inherits from."""
    protocol_names = []
    for base in node.bases:
        name = _extract_name_from_base(base)
        if name:
            protocol_names.append(name)
    return protocol_names


def _node_is_in_class(node: ast.AST, class_node: ast.ClassDef) -> bool:
    """Check if a node is contained within a class."""
    for child in ast.walk(class_node):
        if child is node:
            return True
    return False


def find_parent_class(node: ast.AST, tree: ast.AST) -> ast.ClassDef | None:
    """Find the parent class of a node."""
    for class_node in ast.walk(tree):
        if isinstance(class_node, ast.ClassDef) and _node_is_in_class(node, class_node):
            return class_node
    return None


def is_protocol_file_path(file_path: Path) -> bool:
    """Check if file path suggests it's a protocol/contract file."""
    name_lower = file_path.name.lower()
    return "protocol" in name_lower or "contracts" in name_lower or "ports" in name_lower


def _add_protocol_to_signatures(
    protocol_node: ast.ClassDef, protocol_signatures: dict[str, set[str]]
) -> None:
    """Add protocol class methods to signatures if not already present."""
    if protocol_node.name not in protocol_signatures:
        method_names = {
            child.name
            for child in ast.walk(protocol_node)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        protocol_signatures[protocol_node.name] = method_names


def collect_protocol_classes_from_file(
    tree: ast.AST, protocol_signatures: dict[str, set[str]]
) -> set[str]:
    """Collect Protocol classes defined in this file."""
    protocol_classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_protocol_class(node, tree):
            protocol_classes.add(node.name)
            _add_protocol_to_signatures(node, protocol_signatures)
    return protocol_classes


def _class_implements_protocol(
    class_node: ast.ClassDef, protocol_classes: set[str], protocol_signatures: dict[str, set[str]]
) -> bool:
    """Check if a class implements any known protocol."""
    base_names = get_protocol_base_names(class_node)
    return any(
        base_name in protocol_classes or base_name in protocol_signatures
        for base_name in base_names
    )


def find_protocol_implementing_classes(
    tree: ast.AST, protocol_classes: set[str], protocol_signatures: dict[str, set[str]]
) -> set[str]:
    """Find classes that implement protocols."""
    implementing_classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _class_implements_protocol(
            node, protocol_classes, protocol_signatures
        ):
            implementing_classes.add(node.name)
    return implementing_classes


def _is_protocol_class_method(parent_class: ast.ClassDef, protocol_context: ProtocolContext) -> bool:
    """Check if parent class is a protocol class."""
    return parent_class.name in protocol_context.protocol_classes


def _is_protocol_implementation_method(
    func_name: str, parent_class: ast.ClassDef, protocol_context: ProtocolContext
) -> bool:
    """Check if function is implementing a protocol method."""
    if parent_class.name not in protocol_context.protocol_implementing_classes:
        return False
    return any(
        func_name in method_names
        for method_names in protocol_context.protocol_signatures.values()
    )


def check_if_protocol_method(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    parent_class: ast.ClassDef | None,
    protocol_context: ProtocolContext,
) -> bool:
    """Check if a function is a protocol method."""
    if not parent_class:
        return protocol_context.is_protocol_file
    
    if _is_protocol_class_method(parent_class, protocol_context):
        return True
    
    func_name = func_node.name
    return _is_protocol_implementation_method(func_name, parent_class, protocol_context)


def _find_radon_complexity(
    func_name: str, line_start: int, radon_results: list[Any]
) -> int | None:
    """Find cyclomatic complexity from radon results."""
    if not RADON_AVAILABLE:
        return None
    for radon_func in radon_results:
        if radon_func.name == func_name and radon_func.lineno == line_start:
            return radon_func.complexity
    return None


def _estimate_complexity_from_ast(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Estimate complexity by counting control flow nodes."""
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


def get_cyclomatic_complexity(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    func_name: str,
    line_start: int,
    radon_results: list[Any],
) -> int:
    """Get cyclomatic complexity for a function."""
    radon_complexity = _find_radon_complexity(func_name, line_start, radon_results)
    if radon_complexity is not None:
        return radon_complexity
    return _estimate_complexity_from_ast(func_node)


def _extract_function_bounds(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
    """Extract line start and end from function node."""
    line_start = func_node.lineno
    line_end = func_node.end_lineno if hasattr(func_node, "end_lineno") else line_start
    return line_start, line_end


def _calculate_max_nesting(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate maximum nesting level for a function."""
    visitor = NestingLevelVisitor()
    visitor.visit(func_node)
    return visitor.max_nesting


def analyze_function_node(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    context: FileAnalysisContext,
) -> FunctionMetrics:
    """Analyze a single function node and return metrics."""
    func_name = func_node.name
    line_start, line_end = _extract_function_bounds(func_node)
    function_length = line_end - line_start + 1
    
    parent_class = find_parent_class(func_node, context.tree)
    is_protocol_method = check_if_protocol_method(
        func_node,
        parent_class,
        context.protocol_context,
    )
    
    max_nesting = _calculate_max_nesting(func_node)
    param_count, has_varargs, has_kwargs = count_parameters(func_node)
    cyclomatic_complexity = get_cyclomatic_complexity(
        func_node, func_name, line_start, context.analysis_context.radon_results
    )
    
    return FunctionMetrics(
        file_path=str(context.file_path),
        function_name=func_name,
        line_start=line_start,
        line_end=line_end,
        cyclomatic_complexity=cyclomatic_complexity,
        max_nesting_level=max_nesting,
        function_length=function_length,
        parameter_count=param_count,
        has_varargs=has_varargs,
        has_kwargs=has_kwargs,
        maintainability_index=float(context.analysis_context.mi_score),
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
    
    protocol_context = ProtocolContext(
        protocol_classes=protocol_classes,
        protocol_implementing_classes=protocol_implementing_classes,
        protocol_signatures=protocol_signatures,
        is_protocol_file=is_protocol_file,
    )
    analysis_context = AnalysisContext(
        radon_results=radon_results,
        mi_score=mi_score,
    )
    file_context = FileAnalysisContext(
        file_path=file_path,
        tree=tree,
        protocol_context=protocol_context,
        analysis_context=analysis_context,
    )
    
    metrics: list[FunctionMetrics] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metric = analyze_function_node(node, file_context)
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
    if score >= 10:
        return "🟠 HIGH"
    if score >= 5:
        return "🟡 MEDIUM"
    if score > 0:
        return "🟢 LOW"
    return "✅ OK"


def _prepare_metrics_with_paths(
    top_metrics: list[FunctionMetrics], limit: int, project_root: Path
) -> list[tuple[Path, FunctionMetrics]]:
    """Prepare metrics with relative paths."""
    metrics_with_paths = []
    for m in top_metrics[:limit]:
        try:
            rel_path = Path(m.file_path).relative_to(project_root)
        except ValueError:
            rel_path = Path(m.file_path)
        metrics_with_paths.append((rel_path, m))
    return metrics_with_paths


def _get_default_column_widths() -> dict[str, int]:
    """Get default column widths for table formatting."""
    return {
        'priority': 12,
        'file': 52,
        'function': 32,
        'lines': 12,
        'nest': 6,
        'complex': 8,
        'length': 8,
        'params': 8,
    }


def _calculate_dynamic_column_widths(
    metrics_with_paths: list[tuple[Path, FunctionMetrics]]
) -> dict[str, int]:
    """Calculate dynamic column widths based on content."""
    max_file_len = min(max(len(str(p)) for p, _ in metrics_with_paths), 50)
    max_func_len = min(max(len(m.function_name) for _, m in metrics_with_paths), 30)
    
    widths = _get_default_column_widths()
    widths['file'] = max_file_len + 2
    widths['function'] = max_func_len + 2
    return widths


def _calculate_column_widths(
    metrics_with_paths: list[tuple[Path, FunctionMetrics]]
) -> dict[str, int]:
    """Calculate column widths for table formatting."""
    if not metrics_with_paths:
        return _get_default_column_widths()
    return _calculate_dynamic_column_widths(metrics_with_paths)


def _format_table_header(col_widths: dict[str, int]) -> str:
    """Format table header string."""
    return (
        f"{'Priority':<{col_widths['priority']}} "
        f"{'File':<{col_widths['file']}} "
        f"{'Function':<{col_widths['function']}} "
        f"{'Lines':<{col_widths['lines']}} "
        f"{'Nest':<{col_widths['nest']}} "
        f"{'Complex':<{col_widths['complex']}} "
        f"{'Length':<{col_widths['length']}} "
        f"{'Params':<{col_widths['params']}}"
    )


def _format_parameter_string(metric: FunctionMetrics) -> str:
    """Format parameter count string with *args/**kwargs indicators."""
    param_parts = [str(metric.parameter_count)]
    if metric.has_varargs:
        param_parts.append("*args")
    if metric.has_kwargs:
        param_parts.append("**kwargs")
    return "+".join(param_parts)


def _truncate_string(text: str, max_len: int) -> str:
    """Truncate string to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return "..." + text[-(max_len - 3):]


def _format_table_row(
    rel_path: Path, metric: FunctionMetrics, col_widths: dict[str, int]
) -> str:
    """Format a single table row."""
    file_str = _truncate_string(str(rel_path), col_widths['file'] - 2)
    func_str = _truncate_string(metric.function_name, col_widths['function'] - 2)
    
    return (
        f"{format_priority(metric.priority_score):<{col_widths['priority']}} "
        f"{file_str:<{col_widths['file']}} "
        f"{func_str:<{col_widths['function']}} "
        f"{metric.line_start}-{metric.line_end:<{col_widths['lines']}} "
        f"{metric.max_nesting_level:<{col_widths['nest']}} "
        f"{metric.cyclomatic_complexity:<{col_widths['complex']}} "
        f"{metric.function_length:<{col_widths['length']}} "
        f"{_format_parameter_string(metric):<{col_widths['params']}}"
    )


def print_priority_table(top_metrics: list[FunctionMetrics], limit: int = 30) -> None:
    """Print top priority functions in a tabular format."""
    if not top_metrics:
        return

    project_root = Path(__file__).parent.parent
    metrics_with_paths = _prepare_metrics_with_paths(top_metrics, limit, project_root)
    col_widths = _calculate_column_widths(metrics_with_paths)
    
    header = _format_table_header(col_widths)
    separator = "=" * len(header)
    print(f"\n{separator}")
    print(header)
    print(separator)

    for rel_path, metric in metrics_with_paths:
        print(_format_table_row(rel_path, metric, col_widths))

    print(separator)
    print(f"\nShowing top {min(limit, len(top_metrics))} functions by priority score")
    print("Legend: Nest = Max nesting level, Complex = Cyclomatic complexity, Length = Lines of code, Params = Parameter count")


def _extract_method_names_from_protocol(protocol_node: ast.ClassDef) -> set[str]:
    """Extract method names from a Protocol class node."""
    method_names = set()
    for child in ast.walk(protocol_node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_names.add(child.name)
    return method_names


def _parse_file_safely(file_path: Path) -> ast.AST | None:
    """Parse a Python file, returning None on error."""
    try:
        source_code = file_path.read_text(encoding="utf-8")
        return ast.parse(source_code, filename=str(file_path))
    except Exception:
        return None


def _collect_protocols_from_tree(tree: ast.AST) -> dict[str, set[str]]:
    """Collect protocol signatures from a single AST tree."""
    protocols: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and is_protocol_class(node, tree):
            protocols[node.name] = _extract_method_names_from_protocol(node)
    return protocols


def collect_protocol_signatures(root_dir: Path) -> dict[str, set[str]]:
    """Collect all Protocol class names and their method signatures across all files.
    
    Returns:
        Dictionary mapping protocol class names to sets of method names.
    """
    protocol_signatures: dict[str, set[str]] = {}
    
    for py_file in find_python_files(root_dir):
        tree = _parse_file_safely(py_file)
        if tree is not None:
            protocol_signatures.update(_collect_protocols_from_tree(tree))
    
    return protocol_signatures


def _count_parameter_violations(metrics: list[FunctionMetrics]) -> int:
    """Count parameter violations in metrics."""
    return sum(1 for m in metrics if m.parameter_violation > 0)


def _count_low_mi(metrics: list[FunctionMetrics]) -> int:
    """Count functions with low Maintainability Index (< 20)."""
    return sum(1 for m in metrics if 0 < m.maintainability_index < 20)


def print_summary(
    all_metrics: list[FunctionMetrics],
    regular_metrics: list[FunctionMetrics],
    protocol_metrics: list[FunctionMetrics],
) -> None:
    """Print summary statistics."""
    regular_param_violations = _count_parameter_violations(regular_metrics)
    protocol_param_violations = _count_parameter_violations(protocol_metrics)
    
    print(f"\nTotal functions analyzed: {len(all_metrics)}")
    print(f"  - Regular functions: {len(regular_metrics)}")
    print(f"  - Protocol/interface methods: {len(protocol_metrics)}")
    print(f"Functions with nesting > 2: {_count_violations(regular_metrics, 'nesting')}")
    print(f"Functions with complexity > 10: {_count_violations(regular_metrics, 'complexity')}")
    print(f"Functions with length > 50: {_count_violations(regular_metrics, 'length')}")
    print(f"Functions with too many parameters: {regular_param_violations} (regular) + {protocol_param_violations} (protocol)")
    low_mi_count = _count_low_mi(regular_metrics)
    print(f"Functions with low Maintainability Index (< 20): {low_mi_count}")


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


def _group_metrics_by_file(regular_metrics: list[FunctionMetrics]) -> dict[str, list[FunctionMetrics]]:
    """Group metrics by file path."""
    file_groups: dict[str, list[FunctionMetrics]] = {}
    for metric in regular_metrics:
        if metric.priority_score > 0:
            file_groups.setdefault(metric.file_path, []).append(metric)
    return file_groups


def _format_mi_status(mi: float) -> str:
    """Format Maintainability Index status."""
    if mi == 0:
        return "N/A"
    if mi < 10:
        return f"{mi:.1f} (very difficult)"
    if mi < 20:
        return f"{mi:.1f} (difficult)"
    return f"{mi:.1f} (maintainable)"


def _print_function_details(metric: FunctionMetrics) -> None:
    """Print detailed information about a function metric."""
    print(f"  Function: {metric.function_name} (lines {metric.line_start}-{metric.line_end})")
    print(f"    Priority: {format_priority(metric.priority_score)} ({metric.priority_score:.1f})")
    print(f"    Nesting: {metric.max_nesting_level} (max 2 allowed)")
    print(f"    Complexity: {metric.cyclomatic_complexity} (recommended < 10)")
    print(f"    Length: {metric.function_length} lines (recommended < 50)")
    print(f"    Maintainability Index: {_format_mi_status(metric.maintainability_index)}")
    param_info, max_allowed = format_parameter_info(metric)
    print(f"    Parameters: {param_info} (max {max_allowed} allowed: 4 regular + *args + **kwargs)")
    if metric.parameter_violation > 0:
        print(f"      ⚠️  {metric.parameter_violation} parameter(s) over limit")
    print()


def _print_file_header(file_path: str, file_metrics: list[FunctionMetrics], project_root: Path) -> None:
    """Print header for a file section."""
    rel_path = Path(file_path).relative_to(project_root)
    max_priority = max(m.priority_score for m in file_metrics)
    print(f"\n{format_priority(max_priority)} {rel_path}")
    print("-" * 80)


def _print_file_metrics(file_metrics: list[FunctionMetrics]) -> None:
    """Print metrics for a file."""
    top_metrics = sorted(file_metrics, key=lambda m: m.priority_score, reverse=True)[:5]
    for metric in top_metrics:
        if metric.priority_score <= 0:
            continue
        _print_function_details(metric)


def _get_file_priority(file_metrics: list[FunctionMetrics]) -> float:
    """Get the maximum priority score for a file."""
    return max(m.priority_score for m in file_metrics)


def _sort_files_by_priority(
    file_groups: dict[str, list[FunctionMetrics]]
) -> list[tuple[str, list[FunctionMetrics]]]:
    """Sort files by their highest priority function."""
    return sorted(
        file_groups.items(),
        key=lambda item: _get_file_priority(item[1]),
        reverse=True,
    )


def print_detailed_file_view(regular_metrics: list[FunctionMetrics], project_root: Path) -> None:
    """Print detailed view grouped by file."""
    file_groups = _group_metrics_by_file(regular_metrics)
    sorted_files = _sort_files_by_priority(file_groups)
    
    for file_path, file_metrics in sorted_files[:20]:
        _print_file_header(file_path, file_metrics, project_root)
        _print_file_metrics(file_metrics)


def _has_nesting_violation(metric: FunctionMetrics) -> bool:
    """Check if metric has nesting violation."""
    return metric.max_nesting_level > 2


def _has_complexity_violation(metric: FunctionMetrics) -> bool:
    """Check if metric has complexity violation."""
    return metric.cyclomatic_complexity > 10


def _has_length_violation(metric: FunctionMetrics) -> bool:
    """Check if metric has length violation."""
    return metric.function_length > 50


def _has_parameter_violation(metric: FunctionMetrics) -> bool:
    """Check if metric has parameter violation."""
    return metric.parameter_violation > 0


_VIOLATION_CHECKERS: dict[str, callable] = {
    "nesting": _has_nesting_violation,
    "complexity": _has_complexity_violation,
    "length": _has_length_violation,
    "parameters": _has_parameter_violation,
}


def _count_violations(metrics: list[FunctionMetrics], violation_type: str) -> int:
    """Count violations of a specific type."""
    checker = _VIOLATION_CHECKERS.get(violation_type)
    if checker is None:
        return 0
    return sum(1 for m in metrics if checker(m))


def _build_summary_data(
    all_metrics: list[FunctionMetrics],
    regular_metrics: list[FunctionMetrics],
    protocol_metrics: list[FunctionMetrics],
) -> dict:
    """Build summary statistics dictionary."""
    return {
        "total_functions": len(all_metrics),
        "regular_functions": len(regular_metrics),
        "protocol_methods": len(protocol_metrics),
        "functions_with_nesting_violations": _count_violations(regular_metrics, "nesting"),
        "functions_with_high_complexity": _count_violations(regular_metrics, "complexity"),
        "functions_with_high_length": _count_violations(regular_metrics, "length"),
        "functions_with_too_many_parameters": _count_violations(regular_metrics, "parameters"),
        "protocol_methods_with_too_many_parameters": _count_violations(protocol_metrics, "parameters"),
        "functions_with_low_maintainability_index": _count_low_mi(regular_metrics),
    }


def _metric_to_dict(metric: FunctionMetrics) -> dict:
    """Convert a FunctionMetrics object to a dictionary."""
    return {
        "file": metric.file_path,
        "function": metric.function_name,
        "line_start": metric.line_start,
        "line_end": metric.line_end,
        "cyclomatic_complexity": metric.cyclomatic_complexity,
        "max_nesting_level": metric.max_nesting_level,
        "function_length": metric.function_length,
        "parameter_count": metric.parameter_count,
        "has_varargs": metric.has_varargs,
        "has_kwargs": metric.has_kwargs,
        "parameter_violation": metric.parameter_violation,
        "maintainability_index": metric.maintainability_index,
        "priority_score": metric.priority_score,
        "is_protocol_method": metric.is_protocol_method,
    }


def _should_include_metric(metric: FunctionMetrics) -> bool:
    """Determine if a metric should be included in the report."""
    return metric.priority_score > 0 or (metric.is_protocol_method and metric.parameter_violation > 0)


def generate_json_report(
    all_metrics: list[FunctionMetrics],
    regular_metrics: list[FunctionMetrics],
    protocol_metrics: list[FunctionMetrics],
    report_path: Path,
) -> None:
    """Generate JSON report file."""
    report_data = {
        "summary": _build_summary_data(all_metrics, regular_metrics, protocol_metrics),
        "functions": [
            _metric_to_dict(m)
            for m in all_metrics
            if _should_include_metric(m)
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

