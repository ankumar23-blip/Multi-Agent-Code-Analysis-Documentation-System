"""Repository analysis and intelligent preprocessing module."""
import os
import json
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class CodeChunk:
    """Represents a logical code chunk (function, class, file)."""
    chunk_id: str
    file_path: str
    chunk_type: str  # function, class, file, method
    name: str
    start_line: int
    end_line: int
    language: str
    content: str
    metadata: Dict = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class RepositoryMetadata:
    """Repository metadata and intelligence."""
    repo_type: str  # python, javascript, java, go, rust, etc.
    frameworks: List[str]  # FastAPI, Django, React, etc.
    entry_points: List[str]  # main.py, index.js, etc.
    important_files: List[str]  # Key files for understanding the project
    dependencies: Dict[str, str]  # Package name -> version
    config_files: List[str]  # Config file paths
    important_files_with_types: List[Dict] = None  # Enhanced: [{name, type, size_kb}]
    languages_detail: Dict[str, int] = None  # language -> file count
    readme_text: Optional[str] = None
    extension_counts: Dict[str, int] = None
    total_files: int = 0
    code_files: int = 0
    total_code_chunks: int = 0
    confidence_score: float = 0.85  # 0.0-1.0


class RepositoryAnalyzer:
    """Analyzes repository structure and metadata."""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'go': ['.go'],
        'rust': ['.rs'],
        'cpp': ['.cpp', '.cc', '.cxx', '.h'],
        'c': ['.c', '.h'],
        'ruby': ['.rb'],
        'php': ['.php'],
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        'fastapi': ['from fastapi import', 'import fastapi', 'FastAPI()'],
        'django': ['from django', 'import django', 'Django'],
        'flask': ['from flask import', 'import flask', 'Flask()'],
        'react': ['import React', 'from react', 'React.', 'jsx'],
        'vue': ['import Vue', 'from vue', 'Vue.'],
        'angular': ['@angular', 'import { Component }'],
        'express': ['const express', 'import express', 'require("express")'],
        'spring': ['org.springframework', '@SpringBootApplication', 'Spring'],
    }
    
    # Important files (entry points, configs, etc.)
    IMPORTANT_FILES = {
        'python': [
            'main.py', 'app.py', 'setup.py', 'requirements.txt',
            'pyproject.toml', '__main__.py', 'manage.py', 'wsgi.py'
        ],
        'javascript': [
            'index.js', 'server.js', 'app.js', 'package.json',
            'webpack.config.js', '.babelrc', 'tsconfig.json'
        ],
        'java': [
            'Main.java', 'Application.java', 'pom.xml', 'build.gradle',
            'src/main/java'
        ],
        'go': [
            'main.go', 'go.mod', 'go.sum'
        ],
    }
    
    # Skip patterns
    SKIP_PATTERNS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        '.env', 'dist', 'build', '.next', '.nuxt', 'coverage',
        '.pytest_cache', '*.egg-info', '.cache'
    }
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.metadata = None
        self.code_chunks = []
    
    def analyze(self) -> RepositoryMetadata:
        """Analyze repository and extract code chunks."""
        # Detect languages and frameworks
        languages = self._detect_languages()
        repo_type = self._determine_repo_type(languages)
        frameworks = self._detect_frameworks()
        
        # Find important files and entry points
        entry_points = self._find_entry_points(repo_type)
        important_files = self._find_important_files(repo_type)
        
        # Create detailed file info with types
        important_files_with_types = []
        for file_path in important_files:
            full_path = self.repo_path / file_path
            if os.path.exists(full_path):
                file_ext = os.path.splitext(file_path)[1] or 'no-extension'
                file_size_kb = os.path.getsize(full_path) / 1024
                file_name = os.path.basename(file_path)
                
                important_files_with_types.append({
                    'name': file_name,
                    'path': file_path,
                    'type': file_ext.lstrip('.') or 'file',
                    'size_kb': round(file_size_kb, 2)
                })
        
        # Parse dependencies
        dependencies = self._parse_dependencies(repo_type)
        
        # Extract code chunks from important files
        code_chunks = []
        for file_path in important_files[:20]:  # Limit to 20 files
            chunks = self._extract_code_chunks(file_path)
            code_chunks.extend(chunks)
        
        # Extract README / top-level project description
        readme_text = self._extract_readme_text()

        # Compute language details and code file counts
        languages_detail = languages or {}
        code_files_count = sum(languages_detail.values()) if languages_detail else 0

        # Compute extension counts
        ext_counts = {}
        for f in self.repo_path.rglob('*.*'):
            try:
                if self._should_skip(f):
                    continue
                ext = f.suffix.lower().lstrip('.') or 'noext'
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
            except:
                continue

        # Create metadata
        self.metadata = RepositoryMetadata(
            repo_type=repo_type,
            frameworks=frameworks,
            entry_points=entry_points,
            important_files=important_files,
            important_files_with_types=important_files_with_types,
            dependencies=dependencies,
            config_files=self._find_config_files(),
            languages_detail=languages_detail,
            readme_text=readme_text,
            extension_counts=ext_counts,
            total_files=len(list(self.repo_path.rglob('*'))),
            code_files=code_files_count,
            total_code_chunks=len(code_chunks),
            confidence_score=0.85  # Default confidence
        )
        
        self.code_chunks = code_chunks
        return self.metadata
    
    def _detect_languages(self) -> Dict[str, int]:
        """Detect languages in repository."""
        languages = {}

        # Count files per language by summing counts for all registered extensions
        for lang, exts in self.LANGUAGE_PATTERNS.items():
            total = 0
            for ext in exts:
                files = list(self.repo_path.rglob(f'*{ext}'))
                files = [f for f in files if not self._should_skip(f)]
                total += len(files)
            if total > 0:
                languages[lang] = total

        # If no languages detected, try to infer from config files
        if not languages:
            config_str = str(self._find_config_files()).lower()
            if 'requirements.txt' in config_str or 'pyproject.toml' in config_str:
                languages['python'] = 1
            elif 'package.json' in config_str:
                languages['javascript'] = 1
            elif 'pom.xml' in config_str or 'gradle' in config_str:
                languages['java'] = 1
            elif 'go.mod' in config_str:
                languages['go'] = 1

        return languages

    def _extract_readme_text(self) -> Optional[str]:
        """Extract a short README summary if present."""
        candidates = ['README.md', 'README.rst', 'README.txt', 'README']
        for candidate in candidates:
            matches = list(self.repo_path.rglob(candidate))
            if matches:
                # Prefer file in repo root if available
                matches_sorted = sorted(matches, key=lambda p: len(p.relative_to(self.repo_path).parts))
                try:
                    with open(matches_sorted[0], 'r', encoding='utf-8', errors='ignore') as f:
                        raw = f.read()
                        # Strip markdown headers and return first paragraph
                        text = re.sub(r'#.*\n', '', raw)
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        if paragraphs:
                            summary = paragraphs[0]
                        else:
                            summary = text.strip()
                        return summary[:1000]
                except:
                    continue

        return None
    
    def _determine_repo_type(self, languages: Dict[str, int]) -> str:
        """Determine primary repository type."""
        if not languages:
            return 'unknown'
        
        primary = max(languages.items(), key=lambda x: x[1])[0]
        return primary
    
    def _detect_frameworks(self) -> List[str]:
        """Detect frameworks used in repository."""
        frameworks = set()
        
        # Search through important files for framework imports
        for file_path in self._get_importable_files()[:200]:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                        for pattern in patterns:
                            if pattern.lower() in content.lower():
                                frameworks.add(framework)
                                break
            except:
                pass

        # Also inspect top-level config files and README for framework keywords
        try:
            readme = self._extract_readme_text() or ''
            lower_readme = readme.lower()
            for fw in list(self.FRAMEWORK_PATTERNS.keys()):
                if fw in lower_readme:
                    frameworks.add(fw)
        except:
            pass
        
        return sorted(list(frameworks))
    
    def _find_entry_points(self, repo_type: str) -> List[str]:
        """Find entry point files (main.py, index.js, etc.)."""
        entry_points = []
        
        candidates = self.IMPORTANT_FILES.get(repo_type, [])
        
        for candidate in candidates:
            matching_files = list(self.repo_path.rglob(candidate))
            for f in matching_files:
                if not self._should_skip(f):
                    entry_points.append(str(f.relative_to(self.repo_path)))
        
        return entry_points[:5]  # Limit to top 5
    
    def _find_important_files(self, repo_type: str) -> List[str]:
        """Find important files for analysis."""
        important = []
        
        # Add entry points first
        important.extend(self._find_entry_points(repo_type))
        
        # Add config files
        important.extend(self._find_config_files())
        
        # Add code files by size (larger = more important)
        code_files = self._get_importable_files()
        code_files_with_size = [(f, os.path.getsize(f)) for f in code_files if os.path.exists(f)]
        code_files_with_size.sort(key=lambda x: x[1], reverse=True)
        
        for file_path, _ in code_files_with_size[:30]:
            rel_path = str(Path(file_path).relative_to(self.repo_path))
            if rel_path not in important:
                important.append(rel_path)

        # Ensure README files are considered important
        for readme_candidate in ['README.md', 'README.rst', 'README.txt', 'README']:
            matches = list(self.repo_path.rglob(readme_candidate))
            for f in matches:
                rel = str(Path(f).relative_to(self.repo_path))
                if rel not in important:
                    important.insert(0, rel)
        
        return important[:50]  # Limit to 50 files
    
    def _find_config_files(self) -> List[str]:
        """Find configuration files."""
        config_patterns = [
            'requirements.txt', 'package.json', 'pyproject.toml', 'setup.py',
            'Dockerfile', '.env', '.env.example', 'config.yaml', 'config.json',
            'pom.xml', 'build.gradle', 'go.mod', 'Cargo.toml', 'tsconfig.json'
        ]
        
        config_files = []
        for pattern in config_patterns:
            matches = list(self.repo_path.rglob(pattern))
            for f in matches:
                if not self._should_skip(f):
                    config_files.append(str(f.relative_to(self.repo_path)))
        
        return config_files[:10]
    
    def _parse_dependencies(self, repo_type: str) -> Dict[str, str]:
        """Parse dependencies from config files."""
        dependencies = {}
        
        if repo_type == 'python':
            # Parse requirements.txt or pyproject.toml
            for req_file in ['requirements.txt', 'setup.py', 'pyproject.toml']:
                req_path = self.repo_path / req_file
                if req_path.exists():
                    try:
                        with open(req_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Simple regex to extract package==version
                            matches = re.findall(r'([a-zA-Z0-9_-]+)\s*==\s*([0-9.]+)', content)
                            for pkg, ver in matches[:10]:  # Limit to 10
                                dependencies[pkg] = ver
                    except:
                        pass
        
        elif repo_type == 'javascript':
            # Parse package.json
            pkg_json = self.repo_path / 'package.json'
            if pkg_json.exists():
                try:
                    with open(pkg_json, 'r') as f:
                        data = json.load(f)
                        deps = data.get('dependencies', {})
                        dependencies.update({k: v for k, v in list(deps.items())[:10]})
                except:
                    pass
        
        return dependencies
    
    def _extract_code_chunks(self, file_path: str) -> List[CodeChunk]:
        """Extract logical code chunks (functions, classes) from a file."""
        full_path = self.repo_path / file_path
        
        if not full_path.exists():
            return []
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            return []
        
        # Determine language
        suffix = full_path.suffix.lower()
        language = None
        for lang, exts in self.LANGUAGE_PATTERNS.items():
            if suffix in exts:
                language = lang
                break
        
        if not language:
            return []
        
        chunks = []
        
        # Python code chunking
        if language == 'python':
            chunks = self._chunk_python(file_path, content)
        
        # JavaScript/TypeScript chunking
        elif language in ['javascript', 'typescript']:
            chunks = self._chunk_javascript(file_path, content)
        
        # Generic chunking (by file)
        else:
            chunk = CodeChunk(
                chunk_id=f"{file_path}:0",
                file_path=file_path,
                chunk_type='file',
                name=Path(file_path).name,
                start_line=0,
                end_line=len(content.split('\n')),
                language=language,
                content=content[:2000],  # Limit content
                metadata={'type': 'whole_file'}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_python(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk Python code into functions and classes."""
        chunks = []
        lines = content.split('\n')
        
        # Simple regex-based function/class detection
        func_pattern = r'^def\s+(\w+)\s*\('
        class_pattern = r'^class\s+(\w+)\s*[:\(]'
        
        current_chunk = None
        
        for i, line in enumerate(lines, 1):
            func_match = re.match(func_pattern, line)
            class_match = re.match(class_pattern, line)
            
            if func_match or class_match:
                # Save previous chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Create new chunk
                chunk_type = 'function' if func_match else 'class'
                name = func_match.group(1) if func_match else class_match.group(1)
                
                current_chunk = {
                    'type': chunk_type,
                    'name': name,
                    'start': i,
                    'content_start': i - 1
                }
        
        # Finalize chunks
        if current_chunk:
            current_chunk['end'] = len(lines)
            
            chunk = CodeChunk(
                chunk_id=f"{file_path}:{current_chunk['start']}",
                file_path=file_path,
                chunk_type=current_chunk['type'],
                name=current_chunk['name'],
                start_line=current_chunk['start'],
                end_line=current_chunk['end'],
                language='python',
                content='\n'.join(lines[current_chunk['content_start']:current_chunk['end']])[:2000],
                metadata={'extracted': True}
            )
            chunks.append(chunk)
        
        return chunks[:50]  # Limit to 50 chunks per file
    
    def _chunk_javascript(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code."""
        chunks = []
        lines = content.split('\n')
        
        # Simple function/class detection
        func_pattern = r'(function\s+(\w+)|const\s+(\w+)\s*=|let\s+(\w+)\s*=|async\s+function\s+(\w+)|export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+))'
        class_pattern = r'class\s+(\w+)\s*[{\(]'
        
        for i, line in enumerate(lines, 1):
            func_match = re.search(func_pattern, line)
            class_match = re.search(class_pattern, line)
            
            if func_match or class_match:
                chunk_type = 'class' if class_match else 'function'
                name = class_match.group(1) if class_match else next((g for g in func_match.groups()[1:] if g), 'anonymous')
                
                chunk = CodeChunk(
                    chunk_id=f"{file_path}:{i}",
                    file_path=file_path,
                    chunk_type=chunk_type,
                    name=name,
                    start_line=i,
                    end_line=min(i + 50, len(lines)),
                    language='javascript',
                    content='\n'.join(lines[i-1:min(i+49, len(lines))])[:2000],
                    metadata={'extracted': True}
                )
                chunks.append(chunk)
        
        return chunks[:50]
    
    def _get_importable_files(self) -> List[str]:
        """Get all code files that should be analyzed."""
        files = []
        
        for ext, _ in [(ext, lang) for lang, exts in self.LANGUAGE_PATTERNS.items() for ext in exts]:
            files.extend([str(f) for f in self.repo_path.rglob(f'*{ext}') if not self._should_skip(f)])
        
        return files
    
    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        path_str = str(file_path)
        
        for skip_pattern in self.SKIP_PATTERNS:
            if skip_pattern in path_str:
                return True
        
        return False
