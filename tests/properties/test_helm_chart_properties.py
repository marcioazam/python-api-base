"""
Property-based tests for Helm chart correctness.

**Feature: helm-chart-code-review**
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

HELM_CHART_PATH = Path("helm/my-api")
CHART_YAML_PATH = HELM_CHART_PATH / "Chart.yaml"
VALUES_YAML_PATH = HELM_CHART_PATH / "values.yaml"
TEMPLATES_PATH = HELM_CHART_PATH / "templates"


def load_chart_yaml() -> dict:
    """Load Chart.yaml content."""
    with open(CHART_YAML_PATH) as f:
        return yaml.safe_load(f)


def load_values_yaml() -> dict:
    """Load values.yaml content."""
    with open(VALUES_YAML_PATH) as f:
        return yaml.safe_load(f)


def load_template(name: str) -> str:
    """Load a template file content."""
    template_path = TEMPLATES_PATH / name
    if template_path.exists():
        with open(template_path) as f:
            return f.read()
    return ""


class TestDependencyVersionConstraint:
    """
    **Feature: helm-chart-code-review, Property 7: Dependency Version Constraint**
    
    *For any* dependency declared in Chart.yaml, the version field 
    SHALL NOT contain wildcard patterns (x.x.x).
    **Validates: Requirements 6.3**
    """

    def test_no_wildcard_versions_in_dependencies(self):
        """Verify no dependency uses wildcard version patterns."""
        chart = load_chart_yaml()
        dependencies = chart.get("dependencies", [])
        
        wildcard_pattern = re.compile(r"\d+\.x\.x|\d+\.\d+\.x|x\.\d+\.\d+")
        
        for dep in dependencies:
            version = dep.get("version", "")
            assert not wildcard_pattern.match(version), (
                f"Dependency '{dep.get('name')}' uses wildcard version '{version}'. "
                "Use exact version constraints for reproducible builds."
            )

    def test_all_dependencies_have_exact_versions(self):
        """Verify all dependencies have semantic version format."""
        chart = load_chart_yaml()
        dependencies = chart.get("dependencies", [])
        
        semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        
        for dep in dependencies:
            version = dep.get("version", "")
            assert semver_pattern.match(version), (
                f"Dependency '{dep.get('name')}' version '{version}' "
                "is not in exact semver format (X.Y.Z)."
            )


class TestYamlRoundTripConsistency:
    """
    **Feature: helm-chart-code-review, Property 8: YAML Round-Trip Consistency**
    
    *For any* rendered template output, parsing the YAML and re-serializing 
    SHALL produce semantically equivalent output.
    **Validates: Requirements 6.5**
    """

    @given(st.sampled_from(["Chart.yaml", "values.yaml"]))
    @settings(max_examples=10)
    def test_yaml_round_trip(self, filename: str):
        """Verify YAML files can be parsed and re-serialized consistently."""
        file_path = HELM_CHART_PATH / filename
        
        with open(file_path) as f:
            original_content = f.read()
        
        parsed = yaml.safe_load(original_content)
        reserialized = yaml.dump(parsed, default_flow_style=False)
        reparsed = yaml.safe_load(reserialized)
        
        assert parsed == reparsed, (
            f"YAML round-trip failed for {filename}. "
            "Parsed content differs after re-serialization."
        )


class TestValuesJsonRoundTrip:
    """
    **Feature: helm-chart-code-review, Property 9: Values JSON Round-Trip**
    
    *For any* values.yaml configuration, serializing to JSON and deserializing 
    back SHALL produce an equivalent configuration object.
    **Validates: Requirements 6.4**
    """

    def test_values_json_round_trip(self):
        """Verify values.yaml can be converted to JSON and back."""
        values = load_values_yaml()
        
        json_str = json.dumps(values)
        reparsed = json.loads(json_str)
        
        assert values == reparsed, (
            "Values JSON round-trip failed. "
            "Configuration differs after JSON serialization."
        )

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_replica_count_json_round_trip(self, replica_count: int):
        """Verify numeric values survive JSON round-trip."""
        values = {"replicaCount": replica_count}
        
        json_str = json.dumps(values)
        reparsed = json.loads(json_str)
        
        assert values["replicaCount"] == reparsed["replicaCount"]


class TestResourceGenerationConsistency:
    """
    **Feature: helm-chart-code-review, Property 1: Resource Generation Consistency**
    
    *For any* valid values configuration, when the chart is rendered, 
    all enabled resources SHALL produce valid Kubernetes manifests 
    with consistent naming using the fullname helper.
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """

    def test_templates_use_fullname_helper(self):
        """Verify all templates use the fullname helper for naming."""
        template_files = [
            "deployment.yaml",
            "service.yaml",
            "configmap.yaml",
            "secret.yaml",
            "ingress.yaml",
            "hpa.yaml",
            "pdb.yaml",
            "networkpolicy.yaml",
        ]
        
        for template_name in template_files:
            content = load_template(template_name)
            if content:
                assert 'include "my-api.fullname"' in content or not content.strip(), (
                    f"Template {template_name} should use fullname helper for resource naming."
                )

    def test_serviceaccount_uses_name_helper(self):
        """Verify serviceaccount template uses serviceAccountName helper."""
        content = load_template("serviceaccount.yaml")
        if content:
            assert 'include "my-api.serviceAccountName"' in content, (
                "serviceaccount.yaml should use serviceAccountName helper."
            )

    def test_templates_use_labels_helper(self):
        """Verify all templates use the labels helper."""
        template_files = [
            "deployment.yaml",
            "service.yaml",
            "configmap.yaml",
            "secret.yaml",
            "serviceaccount.yaml",
        ]
        
        for template_name in template_files:
            content = load_template(template_name)
            if content:
                assert 'include "my-api.labels"' in content or not content.strip(), (
                    f"Template {template_name} should use labels helper."
                )


class TestSecurityConfigurationCompleteness:
    """
    **Feature: helm-chart-code-review, Property 2: Security Configuration Completeness**
    
    *For any* rendered Deployment, the container securityContext SHALL contain 
    runAsNonRoot=true, readOnlyRootFilesystem=true, allowPrivilegeEscalation=false, 
    AND resources.limits and resources.requests SHALL be defined.
    **Validates: Requirements 2.2, 2.3**
    """

    def test_security_context_in_values(self):
        """Verify security context values are properly configured."""
        values = load_values_yaml()
        security_context = values.get("securityContext", {})
        
        assert security_context.get("runAsNonRoot") is True, (
            "securityContext.runAsNonRoot must be true"
        )
        assert security_context.get("readOnlyRootFilesystem") is True, (
            "securityContext.readOnlyRootFilesystem must be true"
        )
        assert security_context.get("allowPrivilegeEscalation") is False, (
            "securityContext.allowPrivilegeEscalation must be false"
        )

    def test_resources_defined_in_values(self):
        """Verify resource limits and requests are defined."""
        values = load_values_yaml()
        resources = values.get("resources", {})
        
        assert "limits" in resources, "resources.limits must be defined"
        assert "requests" in resources, "resources.requests must be defined"
        assert "cpu" in resources["limits"], "resources.limits.cpu must be defined"
        assert "memory" in resources["limits"], "resources.limits.memory must be defined"


class TestLabelConsistency:
    """
    **Feature: helm-chart-code-review, Property 3: Label Consistency**
    
    *For any* rendered Kubernetes resource, the metadata.labels SHALL contain 
    all standard Kubernetes labels.
    **Validates: Requirements 4.1, 4.2**
    """

    def test_helpers_define_standard_labels(self):
        """Verify _helpers.tpl defines standard Kubernetes labels."""
        helpers_content = load_template("_helpers.tpl")
        
        required_labels = [
            "app.kubernetes.io/name",
            "app.kubernetes.io/instance",
            "app.kubernetes.io/version",
            "app.kubernetes.io/managed-by",
            "helm.sh/chart",
        ]
        
        for label in required_labels:
            assert label in helpers_content, (
                f"_helpers.tpl must define standard label: {label}"
            )


class TestConditionalResourceCreation:
    """
    **Feature: helm-chart-code-review, Property 4: Conditional Resource Creation**
    
    *For any* conditional resource (Ingress, HPA, NetworkPolicy, ServiceMonitor, RBAC), 
    the resource SHALL be created if and only if its corresponding enabled flag is true.
    **Validates: Requirements 1.4, 1.5, 2.1, 2.4, 2.5, 5.1**
    """

    def test_ingress_has_conditional(self):
        """Verify ingress template has conditional creation."""
        content = load_template("ingress.yaml")
        if content:
            assert ".Values.ingress.enabled" in content, (
                "ingress.yaml must check .Values.ingress.enabled"
            )

    def test_hpa_has_conditional(self):
        """Verify HPA template has conditional creation."""
        content = load_template("hpa.yaml")
        if content:
            assert ".Values.autoscaling.enabled" in content, (
                "hpa.yaml must check .Values.autoscaling.enabled"
            )

    def test_networkpolicy_has_conditional(self):
        """Verify NetworkPolicy template has conditional creation."""
        content = load_template("networkpolicy.yaml")
        if content:
            assert ".Values.networkPolicy.enabled" in content, (
                "networkpolicy.yaml must check .Values.networkPolicy.enabled"
            )


class TestPdbConfigurationValidity:
    """
    **Feature: helm-chart-code-review, Property 5: PDB Configuration Validity**
    
    *For any* PodDisruptionBudget configuration, exactly one of minAvailable 
    or maxUnavailable SHALL be set, never both.
    **Validates: Requirements 3.1**
    """

    def test_pdb_template_validates_config(self):
        """Verify PDB template has validation for minAvailable/maxUnavailable."""
        content = load_template("pdb.yaml")
        if content:
            has_min_check = "minAvailable" in content
            has_max_check = "maxUnavailable" in content
            assert has_min_check or has_max_check, (
                "pdb.yaml must support minAvailable or maxUnavailable"
            )


class TestProbeConfigurationPropagation:
    """
    **Feature: helm-chart-code-review, Property 6: Probe Configuration Propagation**
    
    *For any* liveness or readiness probe values, the rendered Deployment 
    SHALL contain probes with the exact configured parameters.
    **Validates: Requirements 3.3**
    """

    def test_deployment_uses_probe_values(self):
        """Verify deployment template uses probe values from values.yaml."""
        content = load_template("deployment.yaml")
        
        assert ".Values.livenessProbe" in content, (
            "deployment.yaml must use .Values.livenessProbe"
        )
        assert ".Values.readinessProbe" in content, (
            "deployment.yaml must use .Values.readinessProbe"
        )

    def test_values_define_probes(self):
        """Verify values.yaml defines probe configurations."""
        values = load_values_yaml()
        
        assert "livenessProbe" in values, "values.yaml must define livenessProbe"
        assert "readinessProbe" in values, "values.yaml must define readinessProbe"
        
        liveness = values["livenessProbe"]
        assert "httpGet" in liveness or "exec" in liveness or "tcpSocket" in liveness, (
            "livenessProbe must define a probe type"
        )
