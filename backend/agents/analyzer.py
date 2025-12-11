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
    
    # Framework detection patterns (source-code heuristics)
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
        self.code_chunks: List[CodeChunk] = []
    
    async def analyze(self, progress_callback=None) -> RepositoryMetadata:
        """Analyze repository and extract code chunks.

        progress_callback: optional callable accepting (stage:str, percent:float, message:str, file:Optional[str])
        The callback may be sync or async; this method will await it if it's a coroutine.
        """
        import inspect

        async def _maybe_await(cb, *args, **kwargs):
            if not cb:
                return None
            try:
                result = cb(*args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result
            except Exception:
                return None

        # Detect languages and frameworks
        await _maybe_await(progress_callback, 'start', 0.0, 'Starting analysis')
        languages = self._detect_languages()
        await _maybe_await(progress_callback, 'languages_detected', 10.0, f'Languages detected: {languages}')
        repo_type = self._determine_repo_type(languages)
        frameworks = self._detect_frameworks()
        await _maybe_await(progress_callback, 'frameworks_detected', 20.0, f'Frameworks: {frameworks}')
        
        # Find important files and entry points
        entry_points = self._find_entry_points(repo_type)
        important_files = self._find_important_files(repo_type)
        await _maybe_await(progress_callback, 'important_files', 30.0, f'Found {len(important_files)} important files')
        
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
        await _maybe_await(progress_callback, 'dependencies_parsed', 40.0, f'Parsed dependencies: {len(dependencies)} entries')
        
        # Extract code chunks from important files
        code_chunks: List[CodeChunk] = []
        total_imp = max(1, min(len(important_files), 20))
        for idx, file_path in enumerate(important_files[:20], start=1):
            await _maybe_await(progress_callback, 'processing_file', 40.0 + (idx / total_imp) * 30.0, f'Processing {file_path}', file_path)
            chunks = self._extract_code_chunks(file_path)
            code_chunks.extend(chunks)
        
        # Extract README / top-level project description
        readme_text = self._extract_readme_text()
        await _maybe_await(progress_callback, 'readme_parsed', 75.0, 'Extracted README')

        # Compute language details and code file counts
        languages_detail = languages or {}
        code_files_count = sum(languages_detail.values()) if languages_detail else 0

        # Compute extension counts
        ext_counts: Dict[str, int] = {}
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

        await _maybe_await(progress_callback, 'complete', 100.0, 'Analysis complete')
        
        self.code_chunks = code_chunks
        return self.metadata
    
    def _detect_languages(self) -> Dict[str, int]:
        """Detect languages in repository."""
        languages: Dict[str, int] = {}

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
        """Detect frameworks used in repository using code and dependency heuristics."""
        frameworks = set()
        
        # Source-code signal
        for file_path in self._get_importable_files()[:300]:
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

        # Dependency signal: requirements.txt / pyproject.toml
        try:
            req = self.repo_path / 'requirements.txt'
            if req.exists():
                txt = req.read_text(encoding='utf-8', errors='ignore').lower()
                if 'fastapi' in txt:
                    frameworks.add('fastapi')
                if 'flask' in txt:
                    frameworks.add('flask')
                if 'django' in txt:
                    frameworks.add('django')
        except:
            pass

        # Dependency signal: package.json
        try:
            pkg = self.repo_path / 'package.json'
            if pkg.exists():
                data = json.loads(pkg.read_text(encoding='utf-8', errors='ignore'))
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                dkeys = ' '.join(deps.keys()).lower()
                if 'react' in dkeys or 'next' in dkeys:
                    frameworks.add('react')
                if 'vue' in dkeys or '@vue' in dkeys:
                    frameworks.add('vue')
                if 'angular' in dkeys or '@angular' in dkeys:
                    frameworks.add('angular')
                if 'express' in dkeys:
                    frameworks.add('express')
        except:
            pass
        
        return sorted(list(frameworks))
    
    def _find_entry_points(self, repo_type: str) -> List[str]:
        """Find entry point files (main.py, index.js, etc.)."""
        entry_points: List[str] = []
        candidates = self.IMPORTANT_FILES.get(repo_type, [])
        for candidate in candidates:
            matching_files = list(self.repo_path.rglob(candidate))
            for f in matching_files:
                if not self._should_skip(f):
                    entry_points.append(str(f.relative_to(self.repo_path)))
        return entry_points[:5]  # Limit to top 5
    
    def _find_important_files(self, repo_type: str) -> List[str]:
        """Find important files for analysis."""
        important: List[str] = []
        
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
        
        config_files: List[str] = []
        for pattern in config_patterns:
            matches = list(self.repo_path.rglob(pattern))
            for f in matches:
                if not self._should_skip(f):
                    config_files.append(str(f.relative_to(self.repo_path)))
        
        return config_files[:10]
    
    def _parse_dependencies(self, repo_type: str) -> Dict[str, str]:
        """Parse dependencies from config files."""
        dependencies: Dict[str, str] = {}
        
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
                            for pkg, ver in matches[:20]:  # Limit to 20
                                dependencies[pkg] = ver
                    except:
                        pass
        
        elif repo_type == 'javascript':
            # Parse package.json
            pkg_json = self.repo_path / 'package.json'
            if pkg_json.exists():
                try:
                    with open(pkg_json, 'r', encoding='utf-8', errors='ignore') as f:
                        data = json.load(f)
                        deps = data.get('dependencies', {})
                        for k, v in list(deps.items())[:20]:
                            dependencies[k] = v
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
        
        chunks: List[CodeChunk] = []
        
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
        """Chunk Python code into functions and classes.

        Implementation builds proper CodeChunk objects only (no interim dicts),
        preventing 'dict' object has no attribute 'name' errors down the line.
        """
        chunks: List[CodeChunk] = []
        lines = content.split('\n')
        
        # Regex-based function/class detection (allow indentation)
        func_re = re.compile(r'^\s*def\s+(\w+)\s*\(')
        class_re = re.compile(r'^\s*class\s+(\w+)\s*[:\(]')
        
        starts: List[Tuple[int, str, str]] = []  # (start_line, name, chunk_type)
        for i, line in enumerate(lines, 1):
            m_func = func_re.match(line)
            m_class = class_re.match(line)
            if m_func or m_class:
                name = m_func.group(1) if m_func else m_class.group(1)
                ctype = 'function' if m_func else 'class'
                starts.append((i, name, ctype))
        
        if starts:
            for idx, (start_line, name, ctype) in enumerate(starts):
                end_line = (starts[idx + 1][0] - 1) if idx + 1 < len(starts) else len(lines)
                end_line = max(start_line, end_line)
                chunk = CodeChunk(
                    chunk_id=f"{file_path}:{start_line}",
                    file_path=file_path,
                    chunk_type=ctype,
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    language='python',
                    content='\n'.join(lines[start_line - 1:end_line])[:2000],
                    metadata={'extracted': True}
                )
                chunks.append(chunk)
        else:
            # if no identifiable symbols, provide the file as a chunk
            chunk = CodeChunk(
                chunk_id=f"{file_path}:0",
                file_path=file_path,
                chunk_type='file',
                name=Path(file_path).name,
                start_line=0,
                end_line=len(lines),
                language='python',
                content=content[:2000],
                metadata={'type': 'whole_file'}
            )
            chunks.append(chunk)
        
        return chunks[:50]  # Limit to 50 chunks per file
    
    def _chunk_javascript(self, file_path: str, content: str) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code."""
        chunks: List[CodeChunk] = []
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
        files: List[str] = []
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
