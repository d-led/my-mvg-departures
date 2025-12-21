"""Architectural boundary tests using pytest-archon.

These tests verify that the codebase follows clean architecture principles:
- Domain layer has no dependencies on adapters
- Application services don't depend on adapters
- Adapters can depend on domain
- No circular dependencies
"""

from pytest_archon import archrule


def test_domain_models_have_no_dependencies() -> None:
    """Domain models should not import any other modules except standard library and domain itself."""
    (
        archrule("domain models", comment="Domain models should be independent")
        .match("mvg_departures.domain.models*")
        .should_not_import("mvg_departures.adapters*")
        .should_not_import("mvg_departures.application*")
        .should_not_import("mvg_departures.domain.contracts*")
        .should_not_import("mvg_departures.domain.ports*")
        .may_import("mvg_departures.domain.models*")
        .check("mvg_departures")
    )


def test_domain_contracts_have_no_dependencies() -> None:
    """Domain contracts (protocols/interfaces) should not import adapters or application."""
    (
        archrule("domain contracts", comment="Domain contracts should be independent")
        .match("mvg_departures.domain.contracts*")
        .should_not_import("mvg_departures.adapters*")
        .should_not_import("mvg_departures.application*")
        .may_import("mvg_departures.domain.contracts*")
        .may_import("mvg_departures.domain.models*")
        .may_import("mvg_departures.domain.ports*")
        .check("mvg_departures")
    )


def test_domain_ports_have_no_dependencies() -> None:
    """Domain ports (interfaces) should not import adapters or application."""
    (
        archrule("domain ports", comment="Domain ports should be independent")
        .match("mvg_departures.domain.ports*")
        .should_not_import("mvg_departures.adapters*")
        .should_not_import("mvg_departures.application*")
        .may_import("mvg_departures.domain.ports*")
        .may_import("mvg_departures.domain.models*")
        .may_import("mvg_departures.domain.contracts*")
        .check("mvg_departures")
    )


def test_application_services_dont_import_adapters() -> None:
    """Application services should not depend on adapters (infrastructure layer)."""
    (
        archrule(
            "application services", comment="Application services should not depend on adapters"
        )
        .match("mvg_departures.application*")
        .should_not_import("mvg_departures.adapters*")
        .may_import("mvg_departures.domain*")
        .may_import("mvg_departures.application*")
        .check("mvg_departures")
    )


def test_adapters_dont_import_application() -> None:
    """Adapters should not import application services (to avoid cycles)."""
    (
        archrule(
            "adapters independence", comment="Adapters should not depend on application services"
        )
        .match("mvg_departures.adapters*")
        .should_not_import("mvg_departures.application*")
        .may_import("mvg_departures.domain*")
        .may_import("mvg_departures.adapters*")
        .check("mvg_departures", only_direct_imports=True)
    )


def test_no_circular_dependencies_in_domain() -> None:
    """Domain layer should not have circular dependencies."""
    (
        archrule("domain no cycles", comment="Domain layer should not have circular dependencies")
        .match("mvg_departures.domain*")
        .should_not_import("mvg_departures.adapters*")
        .should_not_import("mvg_departures.application*")
        .may_import("mvg_departures.domain*")
        .check("mvg_departures", only_direct_imports=True)
    )


def test_views_dont_import_pyview_app() -> None:
    """Views should not import the main pyview_app module to avoid cycles."""
    (
        archrule("views independence", comment="Views should not import pyview_app")
        .match("mvg_departures.adapters.web.views*")
        .should_not_import("mvg_departures.adapters.web.pyview_app")
        .may_import("mvg_departures.domain*")
        .may_import("mvg_departures.adapters.web.state*")
        .may_import("mvg_departures.adapters.web.presence")
        .may_import("mvg_departures.adapters.web.views*")
        .may_import("mvg_departures.adapters.config*")
        .may_import("mvg_departures.application*")
        .check("mvg_departures")
    )


def test_cli_dont_import_web_adapters() -> None:
    """CLI should not import web adapters to allow running CLI without web server."""
    (
        archrule("CLI independence", comment="CLI should not depend on web adapters")
        .match("mvg_departures.cli")
        .should_not_import("mvg_departures.adapters.web*")
        .may_import("mvg_departures.domain*")
        .may_import("mvg_departures.application*")
        .may_import("mvg_departures.adapters.config*")
        .check("mvg_departures")
    )
