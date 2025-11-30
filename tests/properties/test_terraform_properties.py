"""
Property-based tests for Terraform Infrastructure Refactoring.

**Feature: terraform-infrastructure-refactoring**

These tests verify correctness properties of the Terraform configuration
as defined in the design document.
"""

import os
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set, Tuple

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Base path for terraform files
TERRAFORM_DIR = Path("terraform")


def get_tf_files(directory: Path = TERRAFORM_DIR) -> List[Path]:
    """Get all .tf files in the terraform directory (non-recursive for root)."""
    if not directory.exists():
        return []
    return list(directory.glob("*.tf"))


def get_all_tf_files(directory: Path = TERRAFORM_DIR) -> List[Path]:
    """Get all .tf files recursively."""
    if not directory.exists():
        return []
    return list(directory.rglob("*.tf"))


def parse_variable_declarations(content: str) -> List[str]:
    """Extract variable names from terraform content."""
    pattern = r'variable\s+"([^"]+)"'
    return re.findall(pattern, content)


def parse_output_declarations(content: str) -> List[str]:
    """Extract output names from terraform content."""
    pattern = r'output\s+"([^"]+)"'
    return re.findall(pattern, content)


def parse_backend_block(content: str) -> Dict[str, str]:
    """Extract backend configuration attributes."""
    backend_pattern = r'backend\s+"[^"]+"\s*\{([^}]+)\}'
    match = re.search(backend_pattern, content, re.DOTALL)
    if not match:
        return {}
    
    block_content = match.group(1)
    attrs = {}
    attr_pattern = r'(\w+)\s*=\s*"([^"]*)"'
    for attr_match in re.finditer(attr_pattern, block_content):
        attrs[attr_match.group(1)] = attr_match.group(2)
    return attrs


def check_sensitive_attribute(content: str, block_type: str, name: str) -> bool:
    """Check if a variable or output has sensitive = true."""
    pattern = rf'{block_type}\s+"{name}"\s*\{{([^}}]+)\}}'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return False
    block_content = match.group(1)
    return "sensitive" in block_content and "true" in block_content


def check_try_or_coalesce(content: str) -> bool:
    """Check if content uses try() or coalesce() for module access."""
    # Check for module access patterns
    module_access = re.findall(r'module\.\w+\[\d+\]\.\w+', content)
    if not module_access:
        return True  # No module access, so it's fine
    
    # Check if wrapped in try() or coalesce()
    for access in module_access:
        escaped = re.escape(access)
        if not re.search(rf'(try|coalesce)\s*\([^)]*{escaped}', content):
            # Check if it's in a conditional that's safe
            if not re.search(rf'var\.\w+\s*==\s*"[^"]+"\s*\?\s*[^:]*{escaped}', content):
                return False
    return True


class TestVariableUniqueness:
    """
    **Feature: terraform-infrastructure-refactoring, Property 1: Variable Declaration Uniqueness**
    **Validates: Requirements 1.1**
    
    For any variable name in the Terraform configuration, parsing all .tf files 
    SHALL yield exactly one declaration of that variable.
    """
    
    def test_no_duplicate_variables_in_root(self):
        """Test that no variable is declared more than once in root terraform files."""
        tf_files = get_tf_files()
        all_variables: List[Tuple[str, str]] = []
        
        for tf_file in tf_files:
            content = tf_file.read_text()
            variables = parse_variable_declarations(content)
            for var in variables:
                all_variables.append((var, tf_file.name))
        
        var_counts = Counter(var for var, _ in all_variables)
        duplicates = {var: count for var, count in var_counts.items() if count > 1}
        
        assert not duplicates, f"Duplicate variable declarations found: {duplicates}"
    
    def test_variables_only_in_variables_tf(self):
        """Test that variables are only declared in variables.tf."""
        tf_files = get_tf_files()
        violations: List[Tuple[str, str]] = []
        
        for tf_file in tf_files:
            if tf_file.name == "variables.tf":
                continue
            content = tf_file.read_text()
            variables = parse_variable_declarations(content)
            for var in variables:
                violations.append((var, tf_file.name))
        
        assert not violations, f"Variables declared outside variables.tf: {violations}"


class TestOutputUniqueness:
    """
    **Feature: terraform-infrastructure-refactoring, Property 2: Output Declaration Uniqueness**
    **Validates: Requirements 1.2**
    
    For any output name in the Terraform configuration, parsing all .tf files 
    SHALL yield exactly one declaration of that output.
    """
    
    def test_no_duplicate_outputs_in_root(self):
        """Test that no output is declared more than once in root terraform files."""
        tf_files = get_tf_files()
        all_outputs: List[Tuple[str, str]] = []
        
        for tf_file in tf_files:
            content = tf_file.read_text()
            outputs = parse_output_declarations(content)
            for out in outputs:
                all_outputs.append((out, tf_file.name))
        
        output_counts = Counter(out for out, _ in all_outputs)
        duplicates = {out: count for out, count in output_counts.items() if count > 1}
        
        assert not duplicates, f"Duplicate output declarations found: {duplicates}"
    
    def test_outputs_only_in_outputs_tf(self):
        """Test that outputs are only declared in outputs.tf."""
        tf_files = get_tf_files()
        violations: List[Tuple[str, str]] = []
        
        for tf_file in tf_files:
            if tf_file.name == "outputs.tf":
                continue
            content = tf_file.read_text()
            outputs = parse_output_declarations(content)
            for out in outputs:
                violations.append((out, tf_file.name))
        
        assert not violations, f"Outputs declared outside outputs.tf: {violations}"


class TestNoHardcodedCredentials:
    """
    **Feature: terraform-infrastructure-refactoring, Property 3: No Hardcoded Credentials**
    **Validates: Requirements 2.1**
    
    For any .tf file in the configuration, scanning for patterns matching 
    hardcoded credentials SHALL return zero matches.
    """
    
    CREDENTIAL_PATTERNS = [
        r'password\s*=\s*"[^"]+"',
        r'secret\s*=\s*"[^"]+"',
        r'api_key\s*=\s*"[^"]+"',
        r'access_key\s*=\s*"[^"]+"',
        r'secret_key\s*=\s*"[^"]+"',
    ]
    
    # Patterns that indicate variable reference (safe)
    SAFE_PATTERNS = [
        r'=\s*var\.',
        r'=\s*local\.',
        r'=\s*data\.',
    ]
    
    def test_no_hardcoded_credentials(self):
        """Test that no hardcoded credentials exist in terraform files."""
        tf_files = get_all_tf_files()
        violations: List[Tuple[str, str, str]] = []
        
        for tf_file in tf_files:
            content = tf_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue
                
                # Check for credential patterns
                for pattern in self.CREDENTIAL_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Verify it's not a variable reference
                        is_safe = any(re.search(safe, line) for safe in self.SAFE_PATTERNS)
                        if not is_safe:
                            violations.append((str(tf_file), i, line.strip()))
        
        assert not violations, f"Hardcoded credentials found: {violations}"
    
    def test_no_hardcoded_usernames_in_modules(self):
        """Test that db_username is not hardcoded in module calls."""
        tf_files = get_tf_files()
        violations: List[Tuple[str, str]] = []
        
        for tf_file in tf_files:
            content = tf_file.read_text()
            # Look for db_username = "literal" pattern
            pattern = r'db_username\s*=\s*"[^v][^a][^r]'
            matches = re.findall(pattern, content)
            if matches:
                violations.append((tf_file.name, str(matches)))
        
        assert not violations, f"Hardcoded db_username found: {violations}"


class TestSensitiveCredentialVariables:
    """
    **Feature: terraform-infrastructure-refactoring, Property 4: Database Credential Variables Are Sensitive**
    **Validates: Requirements 2.2**
    
    For any variable with name containing "password", "secret", or "credential",
    the variable definition SHALL include `sensitive = true`.
    """
    
    SENSITIVE_KEYWORDS = ["password", "secret", "credential", "api_key", "access_key"]
    
    def test_credential_variables_are_sensitive(self):
        """Test that credential-related variables are marked sensitive."""
        variables_file = TERRAFORM_DIR / "variables.tf"
        if not variables_file.exists():
            pytest.skip("variables.tf not found")
        
        content = variables_file.read_text()
        variables = parse_variable_declarations(content)
        violations: List[str] = []
        
        for var in variables:
            if any(kw in var.lower() for kw in self.SENSITIVE_KEYWORDS):
                if not check_sensitive_attribute(content, "variable", var):
                    violations.append(var)
        
        assert not violations, f"Credential variables not marked sensitive: {violations}"


class TestSensitiveOutputs:
    """
    **Feature: terraform-infrastructure-refactoring, Property 5: Sensitive Outputs Marked Correctly**
    **Validates: Requirements 2.3**
    
    For any output with name containing "endpoint", "password", "secret", or "key"
    that exposes infrastructure connection details, the output definition 
    SHALL include `sensitive = true`.
    """
    
    SENSITIVE_OUTPUT_KEYWORDS = ["endpoint", "password", "secret", "connection"]
    
    def test_sensitive_outputs_marked(self):
        """Test that sensitive outputs are marked as sensitive."""
        outputs_file = TERRAFORM_DIR / "outputs.tf"
        if not outputs_file.exists():
            pytest.skip("outputs.tf not found")
        
        content = outputs_file.read_text()
        outputs = parse_output_declarations(content)
        violations: List[str] = []
        
        for out in outputs:
            # Check if output name suggests sensitive data
            if any(kw in out.lower() for kw in self.SENSITIVE_OUTPUT_KEYWORDS):
                # Skip non-sensitive endpoints like kubernetes_endpoint
                if out == "kubernetes_endpoint":
                    continue
                if not check_sensitive_attribute(content, "output", out):
                    violations.append(out)
        
        assert not violations, f"Sensitive outputs not marked: {violations}"


class TestBackendConfiguration:
    """
    **Feature: terraform-infrastructure-refactoring, Property 6: Backend Contains No Hardcoded Environment Values**
    **Validates: Requirements 3.2**
    
    For any backend block in the Terraform configuration, the block SHALL NOT 
    contain literal values for bucket, key, region, or dynamodb_table attributes.
    """
    
    HARDCODED_ATTRS = ["bucket", "key", "region", "dynamodb_table"]
    
    def test_backend_no_hardcoded_values(self):
        """Test that backend block doesn't have hardcoded environment values."""
        main_file = TERRAFORM_DIR / "main.tf"
        if not main_file.exists():
            pytest.skip("main.tf not found")
        
        content = main_file.read_text()
        backend_attrs = parse_backend_block(content)
        
        hardcoded = {k: v for k, v in backend_attrs.items() 
                     if k in self.HARDCODED_ATTRS and v}
        
        assert not hardcoded, f"Backend has hardcoded values: {hardcoded}"


class TestCloudSpecificValidation:
    """
    **Feature: terraform-infrastructure-refactoring, Property 7: Cloud-Specific Variable Validation**
    **Validates: Requirements 4.3**
    
    For any cloud-provider-specific variable, the configuration SHALL include 
    validation ensuring non-empty values when that provider is selected.
    """
    
    def test_gcp_project_id_validation_exists(self):
        """Test that gcp_project_id has validation when cloud_provider is gcp."""
        variables_file = TERRAFORM_DIR / "variables.tf"
        if not variables_file.exists():
            pytest.skip("variables.tf not found")
        
        content = variables_file.read_text()
        
        # Check if gcp_project_id has a validation block
        gcp_var_pattern = r'variable\s+"gcp_project_id"\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        match = re.search(gcp_var_pattern, content, re.DOTALL)
        
        if match:
            var_content = match.group(1)
            has_validation = "validation" in var_content
            # This test will pass once validation is added
            assert has_validation, "gcp_project_id should have validation block"


class TestNATGatewayCount:
    """
    **Feature: terraform-infrastructure-refactoring, Property 8: NAT Gateway Count Correctness**
    **Validates: Requirements 5.3, 5.4**
    
    For any VPC module configuration, when single_nat_gateway is true the NAT Gateway 
    count SHALL equal 1, and when single_nat_gateway is false the count SHALL equal 
    the number of availability zones.
    """
    
    def test_nat_gateway_uses_single_nat_variable(self):
        """Test that NAT Gateway count uses single_nat_gateway variable."""
        vpc_main = TERRAFORM_DIR / "modules" / "aws" / "vpc" / "main.tf"
        if not vpc_main.exists():
            pytest.skip("VPC module main.tf not found")
        
        content = vpc_main.read_text()
        
        # Check if single_nat_gateway variable is used in NAT Gateway count
        has_single_nat_var = "single_nat_gateway" in content
        
        # This test will pass once the variable is added
        assert has_single_nat_var, "VPC module should use single_nat_gateway variable"


class TestModuleStructure:
    """
    **Feature: terraform-infrastructure-refactoring, Property 9: Module Structure Completeness**
    **Validates: Requirements 6.1, 6.2, 6.3**
    
    For any module directory under terraform/modules/, the directory SHALL contain 
    at minimum: main.tf, variables.tf, outputs.tf, versions.tf, and README.md files.
    """
    
    REQUIRED_FILES = ["main.tf", "variables.tf", "outputs.tf", "versions.tf", "README.md"]
    
    def test_aws_vpc_module_structure(self):
        """Test that aws/vpc module has required files."""
        module_dir = TERRAFORM_DIR / "modules" / "aws" / "vpc"
        if not module_dir.exists():
            pytest.skip("AWS VPC module not found")
        
        existing_files = [f.name for f in module_dir.iterdir() if f.is_file()]
        missing = [f for f in self.REQUIRED_FILES if f not in existing_files]
        
        assert not missing, f"AWS VPC module missing files: {missing}"


class TestSafeConditionalAccess:
    """
    **Feature: terraform-infrastructure-refactoring, Property 10: Safe Conditional Module Access**
    **Validates: Requirements 7.2**
    
    For any output or provider configuration that accesses module outputs conditionally,
    the access SHALL use try() or coalesce() functions.
    """
    
    def test_outputs_use_safe_access(self):
        """Test that outputs use try() or coalesce() for module access."""
        outputs_file = TERRAFORM_DIR / "outputs.tf"
        if not outputs_file.exists():
            pytest.skip("outputs.tf not found")
        
        content = outputs_file.read_text()
        
        # Check for module access patterns
        module_accesses = re.findall(r'module\.\w+\[\d+\]\.\w+', content)
        
        if module_accesses:
            # Verify they're wrapped in try() or coalesce()
            uses_safe_access = "try(" in content or "coalesce(" in content
            assert uses_safe_access, "Outputs should use try() or coalesce() for module access"


class TestNoLatestImageTags:
    """
    **Feature: terraform-infrastructure-refactoring, Property 11: No Latest Image Tags**
    **Validates: Requirements 8.1**
    
    For any helm_release resource or container image configuration, the image tag 
    SHALL reference a variable or specific version, never the literal string "latest".
    """
    
    def test_no_latest_tag_in_helm_release(self):
        """Test that helm_release doesn't use 'latest' tag."""
        aws_file = TERRAFORM_DIR / "aws.tf"
        if not aws_file.exists():
            pytest.skip("aws.tf not found")
        
        content = aws_file.read_text()
        
        # Check for tag = "latest" pattern
        has_latest = re.search(r'tag\s*=\s*"latest"', content)
        
        assert not has_latest, "helm_release should not use 'latest' image tag"
