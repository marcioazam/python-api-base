"""
Property-based tests for Kubernetes Manifests Refactoring.

**Feature: k8s-manifests-refactoring**

These tests verify correctness properties of the Kubernetes manifests
as defined in the design document.
"""

import os
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

K8S_DIR = Path("k8s")


def load_all_manifests() -> list[dict[str, Any]]:
    """Load all YAML manifests from k8s directory."""
    manifests = []
    if not K8S_DIR.exists():
        return manifests
    
    for yaml_file in K8S_DIR.glob("*.yaml"):
        content = yaml_file.read_text()
        for doc in yaml.safe_load_all(content):
            if doc:
                doc["_source_file"] = yaml_file.name
                manifests.append(doc)
    return manifests


def get_resources_by_kind(kind: str) -> list[dict[str, Any]]:
    """Get all resources of a specific kind."""
    return [m for m in load_all_manifests() if m.get("kind") == kind]


def get_deployments() -> list[dict[str, Any]]:
    """Get all Deployment resources."""
    return get_resources_by_kind("Deployment")


def get_secrets() -> list[dict[str, Any]]:
    """Get all Secret resources."""
    return get_resources_by_kind("Secret")


def get_ingresses() -> list[dict[str, Any]]:
    """Get all Ingress resources."""
    return get_resources_by_kind("Ingress")


def get_services() -> list[dict[str, Any]]:
    """Get all Service resources."""
    return get_resources_by_kind("Service")


def get_network_policies() -> list[dict[str, Any]]:
    """Get all NetworkPolicy resources."""
    return get_resources_by_kind("NetworkPolicy")


def get_pdbs() -> list[dict[str, Any]]:
    """Get all PodDisruptionBudget resources."""
    return get_resources_by_kind("PodDisruptionBudget")


class TestNoPlaintextSecrets:
    """
    **Feature: k8s-manifests-refactoring, Property 1: No Plaintext Secrets**
    **Validates: Requirements 1.2**
    
    For any Secret resource in the k8s directory, the resource SHALL NOT 
    contain plaintext credentials in stringData or data fields with actual values.
    """
    
    CREDENTIAL_PATTERNS = [
        r"password",
        r"secret",
        r"token",
        r"key",
        r"credential",
        r"postgresql://",
        r"mysql://",
        r"redis://",
    ]
    
    def test_no_plaintext_secrets(self):
        """Test that no Secret contains plaintext credentials."""
        secrets = get_secrets()
        violations = []
        
        for secret in secrets:
            name = secret.get("metadata", {}).get("name", "unknown")
            
            # Check stringData
            string_data = secret.get("stringData", {})
            for key, value in string_data.items():
                if isinstance(value, str) and len(value) > 0:
                    # Check if it looks like a real credential
                    for pattern in self.CREDENTIAL_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            violations.append(f"{name}: stringData.{key} contains plaintext")
                            break
            
            # Check data (base64 encoded)
            data = secret.get("data", {})
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 0:
                    violations.append(f"{name}: data.{key} contains encoded value")
        
        assert not violations, f"Plaintext secrets found: {violations}"


class TestNoLatestImageTags:
    """
    **Feature: k8s-manifests-refactoring, Property 2: No Latest Image Tags**
    **Validates: Requirements 2.1**
    
    For any container image specification in Deployment resources, 
    the image tag SHALL NOT be "latest".
    """
    
    def test_no_latest_tags(self):
        """Test that no container uses 'latest' tag."""
        deployments = get_deployments()
        violations = []
        
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                image = container.get("image", "")
                if image.endswith(":latest") or ":" not in image:
                    violations.append(f"{name}/{container.get('name')}: {image}")
        
        assert not violations, f"Containers using 'latest' tag: {violations}"


class TestPodSecurityContext:
    """
    **Feature: k8s-manifests-refactoring, Property 3: Pod Security Context Hardening**
    **Validates: Requirements 3.1, 3.2, 3.4**
    
    For any Pod specification, the securityContext SHALL include 
    runAsNonRoot: true, readOnlyRootFilesystem: true, and allowPrivilegeEscalation: false.
    """
    
    def test_security_context_hardening(self):
        """Test that all containers have proper security context."""
        deployments = get_deployments()
        violations = []
        
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                ctx = container.get("securityContext", {})
                container_name = container.get("name", "unknown")
                
                if not ctx.get("runAsNonRoot"):
                    violations.append(f"{name}/{container_name}: missing runAsNonRoot")
                if not ctx.get("readOnlyRootFilesystem"):
                    violations.append(f"{name}/{container_name}: missing readOnlyRootFilesystem")
                if ctx.get("allowPrivilegeEscalation") is not False:
                    violations.append(f"{name}/{container_name}: allowPrivilegeEscalation not false")
        
        assert not violations, f"Security context violations: {violations}"


class TestCapabilitiesDropped:
    """
    **Feature: k8s-manifests-refactoring, Property 4: Capabilities Dropped**
    **Validates: Requirements 3.3**
    
    For any container securityContext, capabilities SHALL drop ALL.
    """
    
    def test_capabilities_drop_all(self):
        """Test that all containers drop ALL capabilities."""
        deployments = get_deployments()
        violations = []
        
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                ctx = container.get("securityContext", {})
                capabilities = ctx.get("capabilities", {})
                drop = capabilities.get("drop", [])
                
                if "ALL" not in drop:
                    violations.append(f"{name}/{container.get('name')}: capabilities.drop missing ALL")
        
        assert not violations, f"Capabilities not dropped: {violations}"


class TestPDBExists:
    """
    **Feature: k8s-manifests-refactoring, Property 5: PodDisruptionBudget Exists**
    **Validates: Requirements 4.1**
    
    For any Deployment, there SHALL exist a corresponding PodDisruptionBudget resource.
    """
    
    def test_pdb_exists_for_deployments(self):
        """Test that PDB exists for each deployment."""
        deployments = get_deployments()
        pdbs = get_pdbs()
        
        if not deployments:
            pytest.skip("No deployments found")
        
        pdb_selectors = []
        for pdb in pdbs:
            selector = pdb.get("spec", {}).get("selector", {}).get("matchLabels", {})
            pdb_selectors.append(selector)
        
        violations = []
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            labels = deployment.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
            
            has_pdb = any(
                all(labels.get(k) == v for k, v in selector.items())
                for selector in pdb_selectors
                if selector
            )
            
            if not has_pdb:
                violations.append(name)
        
        assert not violations, f"Deployments without PDB: {violations}"


class TestNetworkPolicyExists:
    """
    **Feature: k8s-manifests-refactoring, Property 6: NetworkPolicy Exists**
    **Validates: Requirements 5.1, 5.2**
    
    For any application namespace, there SHALL exist NetworkPolicy resources 
    restricting ingress and egress.
    """
    
    def test_network_policy_exists(self):
        """Test that NetworkPolicy exists with ingress and egress rules."""
        policies = get_network_policies()
        
        if not get_deployments():
            pytest.skip("No deployments found")
        
        has_ingress = any(p.get("spec", {}).get("ingress") for p in policies)
        has_egress = any(p.get("spec", {}).get("egress") for p in policies)
        
        assert policies, "No NetworkPolicy found"
        assert has_ingress, "No NetworkPolicy with ingress rules"
        assert has_egress, "No NetworkPolicy with egress rules"


class TestIngressSecurityHeaders:
    """
    **Feature: k8s-manifests-refactoring, Property 7: Ingress Security Headers**
    **Validates: Requirements 6.2**
    
    For any Ingress resource, annotations SHALL include security headers.
    """
    
    REQUIRED_HEADERS = [
        "X-Frame-Options",
        "X-Content-Type-Options",
    ]
    
    def test_ingress_security_headers(self):
        """Test that Ingress has security header annotations."""
        ingresses = get_ingresses()
        
        if not ingresses:
            pytest.skip("No Ingress found")
        
        violations = []
        for ingress in ingresses:
            name = ingress.get("metadata", {}).get("name", "unknown")
            annotations = ingress.get("metadata", {}).get("annotations", {})
            
            # Check for security headers in annotations
            headers_annotation = annotations.get(
                "nginx.ingress.kubernetes.io/configuration-snippet", ""
            )
            
            for header in self.REQUIRED_HEADERS:
                if header.lower() not in headers_annotation.lower():
                    # Also check add-headers annotation
                    if header.lower() not in str(annotations).lower():
                        violations.append(f"{name}: missing {header}")
        
        assert not violations, f"Missing security headers: {violations}"


class TestIngressClass:
    """
    **Feature: k8s-manifests-refactoring, Property 8: Ingress Class Specification**
    **Validates: Requirements 6.1**
    
    For any Ingress resource, ingressClassName SHALL be specified 
    instead of deprecated kubernetes.io/ingress.class annotation.
    """
    
    def test_ingress_class_not_annotation(self):
        """Test that Ingress uses ingressClassName instead of annotation."""
        ingresses = get_ingresses()
        
        if not ingresses:
            pytest.skip("No Ingress found")
        
        violations = []
        for ingress in ingresses:
            name = ingress.get("metadata", {}).get("name", "unknown")
            annotations = ingress.get("metadata", {}).get("annotations", {})
            spec = ingress.get("spec", {})
            
            has_deprecated = "kubernetes.io/ingress.class" in annotations
            has_ingress_class = "ingressClassName" in spec
            
            if has_deprecated and not has_ingress_class:
                violations.append(f"{name}: uses deprecated annotation")
            if not has_ingress_class:
                violations.append(f"{name}: missing ingressClassName")
        
        assert not violations, f"Ingress class violations: {violations}"


class TestPrometheusAnnotations:
    """
    **Feature: k8s-manifests-refactoring, Property 9: Prometheus Annotations**
    **Validates: Requirements 7.1**
    
    For any Deployment, pod template annotations SHALL include prometheus.io/scrape.
    """
    
    def test_prometheus_scrape_annotation(self):
        """Test that Deployments have Prometheus scrape annotations."""
        deployments = get_deployments()
        
        if not deployments:
            pytest.skip("No deployments found")
        
        violations = []
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            annotations = deployment.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
            
            if "prometheus.io/scrape" not in annotations:
                violations.append(name)
        
        assert not violations, f"Deployments without Prometheus annotations: {violations}"


class TestKubernetesRecommendedLabels:
    """
    **Feature: k8s-manifests-refactoring, Property 10: Kubernetes Recommended Labels**
    **Validates: Requirements 8.2**
    
    For any resource in k8s directory, metadata.labels SHALL include app.kubernetes.io/name.
    """
    
    def test_recommended_labels(self):
        """Test that resources have Kubernetes recommended labels."""
        manifests = load_all_manifests()
        
        if not manifests:
            pytest.skip("No manifests found")
        
        violations = []
        for manifest in manifests:
            kind = manifest.get("kind", "unknown")
            name = manifest.get("metadata", {}).get("name", "unknown")
            labels = manifest.get("metadata", {}).get("labels", {})
            
            if "app.kubernetes.io/name" not in labels:
                violations.append(f"{kind}/{name}")
        
        assert not violations, f"Resources without recommended labels: {violations}"


class TestDeploymentStrategy:
    """
    **Feature: k8s-manifests-refactoring, Property 11: Deployment Strategy Configuration**
    **Validates: Requirements 9.1**
    
    For any Deployment, strategy SHALL be RollingUpdate with maxSurge and maxUnavailable configured.
    """
    
    def test_rolling_update_strategy(self):
        """Test that Deployments use RollingUpdate strategy."""
        deployments = get_deployments()
        
        if not deployments:
            pytest.skip("No deployments found")
        
        violations = []
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            strategy = deployment.get("spec", {}).get("strategy", {})
            
            if strategy.get("type") != "RollingUpdate":
                violations.append(f"{name}: strategy not RollingUpdate")
            
            rolling = strategy.get("rollingUpdate", {})
            if "maxSurge" not in rolling:
                violations.append(f"{name}: missing maxSurge")
            if "maxUnavailable" not in rolling:
                violations.append(f"{name}: missing maxUnavailable")
        
        assert not violations, f"Deployment strategy violations: {violations}"


class TestStartupProbe:
    """
    **Feature: k8s-manifests-refactoring, Property 12: Startup Probe Configuration**
    **Validates: Requirements 4.4**
    
    For any container in Deployment, startupProbe SHALL be configured.
    """
    
    def test_startup_probe_exists(self):
        """Test that containers have startupProbe configured."""
        deployments = get_deployments()
        
        if not deployments:
            pytest.skip("No deployments found")
        
        violations = []
        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            for container in containers:
                if "startupProbe" not in container:
                    violations.append(f"{name}/{container.get('name')}")
        
        assert not violations, f"Containers without startupProbe: {violations}"
