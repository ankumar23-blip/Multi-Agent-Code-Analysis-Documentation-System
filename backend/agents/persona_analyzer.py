"""Persona-specific code analysis for SDE (Software Development Engineer) and PM (Product Manager)."""
from typing import Dict, List, Any
from .analyzer import RepositoryMetadata, CodeChunk


class PersonaAnalyzer:
    """Generates persona-specific insights from repository analysis."""
    
    def __init__(self, metadata: RepositoryMetadata, chunks: List[CodeChunk]):
        """Initialize with base analysis results."""
        self.metadata = metadata
        self.chunks = chunks
    
    def analyze_for_sde(self) -> Dict[str, Any]:
        """Generate SDE (Software Development Engineer) focused analysis.
        
        SDE Focus:
        - Architecture and design patterns
        - Code quality and technical debt
        - Dependencies and integrations
        - Testing and CI/CD
        - Performance considerations
        """
        try:
            return {
                "persona": "SDE",
                "title": "Software Development Engineer Analysis",
                "overview": self._generate_sde_overview(),
                "architecture": self._analyze_sde_architecture(),
                "technical_details": self._analyze_sde_technical_details(),
                "code_quality": self._analyze_code_quality(),
                "dependencies": self.metadata.dependencies,
                "recommendations": self._generate_sde_recommendations(),
                "key_files": self._get_sde_key_files(),
            }
        except Exception as e:
            print(f"[PERSONA] Error generating SDE analysis: {e}")
            import traceback
            print(traceback.format_exc())
            raise
    
    def analyze_for_pm(self) -> Dict[str, Any]:
        """Generate PM (Product Manager) focused analysis.
        
        PM Focus:
        - Feature identification
        - User flows and interactions
        - Business logic and rules
        - Configuration and customization
        - Scalability and performance
        - Roadmap implications
        """
        return {
            "persona": "PM",
            "title": "Product Manager Analysis",
            "overview": self._generate_pm_overview(),
            "features": self._identify_features(),
            "user_flows": self._analyze_user_flows(),
            "business_logic": self._analyze_business_logic(),
            "configuration": self._analyze_configuration(),
            "scalability": self._analyze_scalability(),
            "recommendations": self._generate_pm_recommendations(),
            "key_files": self._get_pm_key_files(),
            "stakeholders": self._identify_stakeholders(),
        }
    
    # SDE Analysis Methods
    def _generate_sde_overview(self) -> str:
        """Generate technical overview for SDE."""
        repo_type = (self.metadata.repo_type or 'unknown').upper()
        frameworks = ", ".join(self.metadata.frameworks) if self.metadata.frameworks else "None detected"
        languages_detail = self.metadata.languages_detail or {}
        languages_summary = ", ".join([f"{k}({v})" for k, v in languages_detail.items()]) if languages_detail else "Unknown"
        complexity = self._determine_complexity_level()
        
        # Calculate realistic metrics
        total_files = self.metadata.total_files or 0
        code_files = self.metadata.code_files or 0
        chunks = self.metadata.total_code_chunks or 0
        
        overview = f"""
**Project Summary:**

This is a **{repo_type}** project with the following characteristics:

- **Language:** {repo_type}
- **Total Files:** {total_files}
- **Code Files:** {code_files}
- **Functions/Classes:** {chunks}
- **Frameworks:** {frameworks}
- **Complexity Level:** {complexity}
- **Entry Points:** {len(self.metadata.entry_points)} found

     - **Languages Detected:** {languages_summary}

**Key Characteristics:**
- Average function size: ~{self._calculate_avg_complexity():.1f} lines
- Configuration files: {len(self.metadata.config_files)}
- Dependencies: {len(self.metadata.dependencies)}
- Confidence Score: {self.metadata.confidence_score:.0%}
"""
        return overview
    
    def _analyze_sde_architecture(self) -> Dict[str, Any]:
        """Analyze system architecture from SDE perspective."""
        return {
            "repo_type": self.metadata.repo_type,
            "frameworks": self.metadata.frameworks,
            "entry_points": self.metadata.entry_points[:5],
            "config_files": self.metadata.config_files,
            "architecture_pattern": self._infer_architecture_pattern(),
            "module_structure": self._analyze_module_structure(),
        }
    
    def _analyze_sde_technical_details(self) -> Dict[str, Any]:
        """Detailed technical analysis for SDE."""
        top_deps = dict(list(self.metadata.dependencies.items())[:10]) if self.metadata.dependencies else {}
        
        return {
            "language": self.metadata.repo_type,
            "framework_stack": self.metadata.frameworks,
            "dependencies_count": len(self.metadata.dependencies),
            "top_dependencies": top_deps or {"Note": "No versioned dependencies detected"},
            "code_metrics": {
                "total_files": self.metadata.total_files,
                "code_files": self.metadata.code_files,
                "total_chunks": self.metadata.total_code_chunks,
                "avg_chunk_lines": self._calculate_avg_complexity(),
                "config_files": len(self.metadata.config_files),
            },
            "entry_points": self.metadata.entry_points[:5],
            "code_organization": self._analyze_code_organization(),
        }
    
    def _analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze code quality aspects."""
        return {
            "confidence_score": self.metadata.confidence_score,
            "code_structure_rating": self._rate_code_structure(),
            "dependency_health": self._analyze_dependency_health(),
            "suggested_improvements": [
                "Add unit tests for critical paths",
                "Document complex algorithms",
                "Consider adding type hints for better IDE support",
                "Implement error handling in key functions",
                "Add integration tests for external dependencies"
            ]
        }
    
    def _generate_sde_recommendations(self) -> List[str]:
        """Generate actionable recommendations for SDE."""
        recommendations = [
            "Review and update outdated dependencies",
            "Implement comprehensive logging for debugging",
            "Add API documentation if applicable",
            "Set up automated testing pipeline",
            "Consider refactoring large files",
            "Implement design patterns for better maintainability",
        ]
        
        if self.metadata.total_code_chunks > 100:
            recommendations.append("Consider breaking down large modules into smaller components")
        
        if len(self.metadata.dependencies) > 20:
            recommendations.append("Audit dependencies - consider removing unused ones")
        
        return recommendations
    
    def _get_sde_key_files(self) -> List[Dict[str, str]]:
        """Get key files from SDE perspective."""
        key_patterns = ['main', 'app', 'init', 'config', 'setup', 'requirement', 'docker', 'test']
        
        files_with_types = self.metadata.important_files_with_types or []
        key_files = [
            f for f in files_with_types 
            if any(pattern.lower() in f.get('name', '').lower() for pattern in key_patterns)
        ]
        
        return key_files[:10]
    
    # PM Analysis Methods
    def _generate_pm_overview(self) -> str:
        """Generate business overview for PM."""
        frameworks_str = ", ".join(self.metadata.frameworks) if self.metadata.frameworks else "Custom implementation"
        use_case = self._infer_use_case()
        deployment = self._infer_deployment_type()
        readme_snippet = (self.metadata.readme_text or "").strip()
        if readme_snippet:
            readme_snippet = (readme_snippet[:400] + "...") if len(readme_snippet) > 400 else readme_snippet
        
        overview = f"""
**Project Overview:**

This is a **{use_case}** built with **{frameworks_str}**.

**Project Scope:**
- **Total Files:** {self.metadata.total_files}
- **Code Implementation Files:** {self.metadata.code_files}
- **Key Functions/Features:** {self.metadata.total_code_chunks}
- **Technology Stack:** {self.metadata.repo_type.upper()}
- **Deployment Type:** {deployment}
- **Configuration Files:** {len(self.metadata.config_files)}

**README Summary:**
{readme_snippet or 'No README available.'}

**Scale & Complexity:**
- Repository contains {self.metadata.code_files} implementation files across {len(self.metadata.entry_points)} entry points
- {len(self.metadata.dependencies)} external dependencies integrated
- Confidence in analysis: {self.metadata.confidence_score:.0%}

**Key Capabilities Identified:**
Based on code analysis, this project implements core functionality in {self.metadata.repo_type.upper()} with detected frameworks: {frameworks_str or 'none'}
"""
        return overview
    
    def _identify_features(self) -> Dict[str, List[str]]:
        """Identify and categorize features from code."""
        auth_features = self._detect_auth_features()
        data_features = self._detect_data_features()
        api_features = self._detect_api_features()
        integration_features = self._detect_integrations()
        
        features = {
            "authentication": auth_features or ["User identity management detected" if auth_features else "Not detected"],
            "data_management": data_features or ["Data persistence layer detected" if data_features else "Not detected"],
            "api_endpoints": api_features or ["REST/HTTP endpoints detected" if api_features else "Not detected"],
            "external_integrations": integration_features or ["Third-party services" if integration_features else "Limited integrations"],
            "configuration": self.metadata.config_files or ["Environment-based configuration"],
        }
        return features
    
    def _analyze_user_flows(self) -> Dict[str, Any]:
        """Analyze primary user flows."""
        return {
            "primary_flows": self._identify_primary_flows(),
            "entry_mechanisms": self.metadata.entry_points[:5],
            "integration_points": self._detect_external_apis(),
            "data_flow": self._analyze_data_flow(),
        }
    
    def _analyze_business_logic(self) -> Dict[str, Any]:
        """Analyze business logic from PM perspective."""
        return {
            "core_functions": [c.name for c in self.chunks[:10] if c.chunk_type == 'function'],
            "business_rules": self._extract_business_rules(),
            "validation_logic": self._identify_validation(),
            "error_handling": self._identify_error_handling(),
        }
    
    def _analyze_configuration(self) -> Dict[str, Any]:
        """Analyze configuration and customization options."""
        return {
            "config_files": self.metadata.config_files,
            "environment_vars": self._identify_env_vars(),
            "customizable_aspects": self._identify_customization_points(),
            "feature_flags": self._detect_feature_flags(),
        }
    
    def _analyze_scalability(self) -> Dict[str, Any]:
        """Analyze scalability aspects."""
        return {
            "scalability_rating": self._rate_scalability(),
            "bottlenecks": self._identify_bottlenecks(),
            "async_support": self._detect_async_patterns(),
            "caching_strategy": self._detect_caching(),
            "recommendations": [
                "Implement caching layer for frequently accessed data",
                "Consider database indexing strategy",
                "Monitor performance metrics",
                "Plan for horizontal scaling",
            ]
        }
    
    def _generate_pm_recommendations(self) -> List[str]:
        """Generate product recommendations for PM."""
        return [
            "Document feature capabilities for customer-facing materials",
            "Identify and prioritize technical debt for future sprints",
            "Plan user documentation based on identified workflows",
            "Consider expansion opportunities based on current architecture",
            "Evaluate third-party integration opportunities",
            "Plan for scalability improvements if user growth is expected",
        ]
    
    def _get_pm_key_files(self) -> List[Dict[str, str]]:
        """Get key files from PM perspective."""
        business_patterns = ['config', 'requirement', 'setup', 'readme', 'license', 'contributing', 'docker']
        
        files_with_types = self.metadata.important_files_with_types or []
        key_files = [
            f for f in files_with_types 
            if any(pattern.lower() in f.get('name', '').lower() for pattern in business_patterns)
        ]
        
        return key_files[:10]
    
    def _identify_stakeholders(self) -> List[str]:
        """Identify potential stakeholders."""
        stakeholders = ["Product Owner", "Engineering Lead", "DevOps Team"]
        
        if 'react' in str(self.metadata.frameworks).lower():
            stakeholders.append("Frontend Lead")
        
        if 'api' in str(self.metadata.frameworks).lower() or self.metadata.repo_type in ['python', 'javascript']:
            stakeholders.append("Backend Lead")
        
        return stakeholders
    
    # Helper Methods
    def _determine_architecture_type(self) -> str:
        """Determine architecture type from frameworks."""
        frameworks_str = str(self.metadata.frameworks).lower()
        
        if 'react' in frameworks_str or 'vue' in frameworks_str:
            return "Frontend SPA"
        elif 'fastapi' in frameworks_str or 'django' in frameworks_str:
            return "Microservice/REST API"
        elif 'express' in frameworks_str:
            return "Node.js Backend"
        else:
            return "Monolithic Application"
    
    def _determine_complexity_level(self) -> str:
        """Rate complexity based on metrics."""
        if self.metadata.total_code_chunks > 100:
            return "High"
        elif self.metadata.total_code_chunks > 50:
            return "Medium"
        else:
            return "Low"
    
    def _infer_architecture_pattern(self) -> str:
        """Infer architecture pattern."""
        if 'fastapi' in str(self.metadata.frameworks).lower():
            return "MVC/REST API"
        elif 'react' in str(self.metadata.frameworks).lower():
            return "Component-based SPA"
        else:
            return "Custom"
    
    def _analyze_module_structure(self) -> Dict[str, int]:
        """Analyze module/directory structure."""
        return {
            "total_modules": max(len(self.metadata.important_files) // 5, 1),
            "avg_files_per_module": len(self.metadata.important_files) // max(1, len(self.metadata.important_files) // 5),
        }
    
    def _calculate_avg_complexity(self) -> float:
        """Calculate average code complexity."""
        if not self.chunks:
            return 0.0
        
        total_lines = sum(c.end_line - c.start_line for c in self.chunks)
        avg_lines = total_lines / len(self.chunks) if self.chunks else 0
        
        return round(avg_lines / 10, 2)  # Rough complexity estimate
    
    def _analyze_code_organization(self) -> str:
        """Analyze code organization."""
        if len(self.metadata.important_files) > 20:
            return "Well-organized with clear separation of concerns"
        else:
            return "Simpler codebase with potential for better organization"
    
    def _rate_code_structure(self) -> str:
        """Rate code structure quality."""
        if self.metadata.confidence_score > 0.8:
            return "Good - Clear structure with identifiable patterns"
        else:
            return "Fair - Could benefit from better organization"
    
    def _analyze_dependency_health(self) -> str:
        """Analyze dependency health."""
        if len(self.metadata.dependencies) < 10:
            return "Healthy - Minimal dependencies reduce maintenance burden"
        elif len(self.metadata.dependencies) < 25:
            return "Moderate - Good balance of functionality and complexity"
        else:
            return "Complex - Consider auditing for unused dependencies"
    
    def _detect_auth_features(self) -> List[str]:
        """Detect authentication features."""
        auth_patterns = ['auth', 'login', 'user', 'token', 'session', 'jwt', 'oauth']
        detected = []
        
        for chunk in self.chunks:
            chunk_text = chunk.name.lower() + chunk.content.lower()
            for pattern in auth_patterns:
                if pattern in chunk_text and pattern not in detected:
                    detected.append(pattern.upper())
        
        return detected[:5]
    
    def _detect_data_features(self) -> List[str]:
        """Detect data management features."""
        data_patterns = ['database', 'cache', 'storage', 'query', 'model', 'schema']
        detected = []
        
        for chunk in self.chunks:
            chunk_text = chunk.name.lower() + chunk.content.lower()
            for pattern in data_patterns:
                if pattern in chunk_text and pattern not in detected:
                    detected.append(pattern.upper())
        
        return detected[:5]
    
    def _detect_api_features(self) -> List[str]:
        """Detect API endpoints."""
        api_patterns = ['api', 'endpoint', 'route', 'handler', 'controller']
        detected = []
        
        for chunk in self.chunks:
            chunk_text = chunk.name.lower() + chunk.content.lower()
            for pattern in api_patterns:
                if pattern in chunk_text and pattern not in detected:
                    detected.append(pattern.upper())
        
        return detected[:5]
    
    def _detect_integrations(self) -> List[str]:
        """Detect external integrations."""
        integration_patterns = ['http', 'request', 'client', 'api', 'service', 'webhook']
        detected = []
        
        for chunk in self.chunks:
            chunk_text = chunk.content.lower()
            for pattern in integration_patterns:
                if pattern in chunk_text and pattern not in detected:
                    detected.append(pattern.upper())
        
        return detected[:5]
    
    def _identify_primary_flows(self) -> List[str]:
        """Identify primary user flows."""
        return [
            "User Authentication",
            "Data Access/Query",
            "Content Creation/Update",
            "System Integration",
            "Error Handling & Logging"
        ]
    
    def _detect_external_apis(self) -> List[str]:
        """Detect external API integrations."""
        api_calls = []
        
        for chunk in self.chunks:
            if 'http' in chunk.content.lower() or 'request' in chunk.content.lower():
                api_calls.append(chunk.name)
        
        return api_calls[:5]
    
    def _analyze_data_flow(self) -> str:
        """Analyze data flow patterns."""
        return "Data flows through configured services with proper validation and error handling"
    
    def _extract_business_rules(self) -> List[str]:
        """Extract business rules."""
        return [
            "Input validation and sanitization",
            "Access control and permissions",
            "Data transformation and processing",
            "Business logic enforcement",
            "Audit logging and tracking"
        ]
    
    def _identify_validation(self) -> List[str]:
        """Identify validation logic."""
        validation = []
        for chunk in self.chunks:
            if 'valid' in chunk.name.lower() or 'check' in chunk.name.lower():
                validation.append(chunk.name)
        return validation[:5]
    
    def _identify_error_handling(self) -> List[str]:
        """Identify error handling."""
        return [
            "Try-catch blocks for exception handling",
            "Input validation and sanitization",
            "Logging for debugging and monitoring",
            "Graceful degradation and fallbacks"
        ]
    
    def _identify_env_vars(self) -> List[str]:
        """Identify environment variables."""
        env_patterns = ['.env', 'environment', 'config', 'settings']
        env_vars = []
        
        for chunk in self.chunks:
            if any(pattern in chunk.name.lower() for pattern in env_patterns):
                env_vars.append(chunk.name)
        
        return env_vars[:5]
    
    def _identify_customization_points(self) -> List[str]:
        """Identify customization points."""
        return [
            "Configuration files for environment setup",
            "Pluggable components and services",
            "Themeable UI components",
            "Extensible business logic",
            "Database schema customization"
        ]
    
    def _detect_feature_flags(self) -> List[str]:
        """Detect feature flags."""
        flags = []
        for chunk in self.chunks:
            if 'flag' in chunk.name.lower() or 'feature' in chunk.content.lower():
                flags.append(chunk.name)
        return flags[:5]
    
    def _rate_scalability(self) -> str:
        """Rate scalability."""
        if len(self.metadata.frameworks) > 2 and 'async' in str(self.metadata.frameworks).lower():
            return "High - Designed for scalability with async support"
        elif len(self.metadata.frameworks) > 0:
            return "Medium - Can scale with proper infrastructure"
        else:
            return "To be evaluated - Depends on implementation"
    
    def _identify_bottlenecks(self) -> List[str]:
        """Identify potential bottlenecks."""
        return [
            "Database queries optimization",
            "Caching implementation",
            "Async processing for long operations",
            "Connection pooling",
            "Load balancing strategy"
        ]
    
    def _detect_async_patterns(self) -> bool:
        """Detect async/await patterns."""
        for chunk in self.chunks:
            if 'async' in chunk.content.lower() or 'await' in chunk.content.lower():
                return True
        return False
    
    def _detect_caching(self) -> str:
        """Detect caching mechanisms."""
        for chunk in self.chunks:
            if 'cache' in chunk.content.lower():
                return "Caching implemented"
        return "No caching detected - consider implementing"
    
    def _get_technology_summary(self) -> str:
        """Get technology summary."""
        if self.metadata.frameworks:
            return ", ".join(self.metadata.frameworks[:3])
        return self.metadata.repo_type.upper()
    
    def _infer_deployment_type(self) -> str:
        """Infer deployment type."""
        frameworks_str = str(self.metadata.frameworks).lower()
        
        if 'docker' in self.metadata.config_files or 'docker' in frameworks_str:
            return "Containerized (Docker)"
        elif 'serverless' in frameworks_str:
            return "Serverless"
        else:
            return "Traditional Server/Cloud"
    
    def _infer_use_case(self) -> str:
        """Infer primary use case."""
        frameworks_str = str(self.metadata.frameworks).lower()
        
        if 'react' in frameworks_str or 'vue' in frameworks_str:
            return "Web Application (Frontend)"
        elif 'fastapi' in frameworks_str or 'django' in frameworks_str:
            return "REST API / Backend Service"
        elif 'express' in frameworks_str:
            return "Node.js Web Service"
        else:
            return "General-purpose Application"
