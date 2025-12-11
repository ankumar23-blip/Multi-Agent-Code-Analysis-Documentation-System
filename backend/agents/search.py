"""Semantic search and code discovery module."""
from typing import List, Dict, Tuple
from .analyzer import CodeChunk


class SemanticSearchEngine:
    """Search and find relevant code chunks based on queries."""
    
    def __init__(self, code_chunks: List[CodeChunk]):
        self.code_chunks = code_chunks
        self.index = self._build_index()
    
    def _build_index(self) -> Dict[str, List[CodeChunk]]:
        """Build search index from code chunks."""
        index = {}
        
        for chunk in self.code_chunks:
            # Index by chunk name
            if chunk.name:
                key = chunk.name.lower()
                if key not in index:
                    index[key] = []
                index[key].append(chunk)
            
            # Index by chunk type
            chunk_type_key = f"type:{chunk.chunk_type}"
            if chunk_type_key not in index:
                index[chunk_type_key] = []
            index[chunk_type_key].append(chunk)
            
            # Index by file
            file_key = f"file:{chunk.file_path}".lower()
            if file_key not in index:
                index[file_key] = []
            index[file_key].append(chunk)
            
            # Index by keywords from content and file path/name tokens
            keywords = self._extract_keywords(chunk.content)
            # include file path tokens and chunk name tokens
            import re
            path_tokens = [p for p in re.split(r'[^a-zA-Z0-9]+', chunk.file_path) if p]
            keywords.extend(path_tokens)
            if chunk.name:
                keywords.extend([p for p in re.split(r'[^a-zA-Z0-9]+', chunk.name) if p])

            for keyword in set([k for k in keywords if k]):
                key = keyword.lower()
                if key not in index:
                    index[key] = []
                index[key].append(chunk)
        
        return index
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for relevant code chunks.
        
        Returns: List of dicts with chunk info and relevance score
        """
        import re
        query_lower = query.lower()
        query_terms = set([t for t in re.split(r'[^a-zA-Z0-9]+', query_lower) if len(t) > 1])
        
        # Find matching chunks
        matches = {}
        
        for term in query_terms:
            # Direct index lookup
            if term in self.index:
                for chunk in self.index[term]:
                    chunk_id = chunk.chunk_id
                    if chunk_id not in matches:
                        matches[chunk_id] = {'chunk': chunk, 'score': 0}
                    matches[chunk_id]['score'] += 2.0
            
            # Fuzzy matching in chunk names and content
            for chunk in self.code_chunks:
                chunk_id = chunk.chunk_id
                
                # Name matching
                if chunk.name and term in chunk.name.lower():
                    if chunk_id not in matches:
                        matches[chunk_id] = {'chunk': chunk, 'score': 0}
                    matches[chunk_id]['score'] += 1.5
                
                # Content matching
                if term in chunk.content.lower():
                    if chunk_id not in matches:
                        matches[chunk_id] = {'chunk': chunk, 'score': 0}
                    matches[chunk_id]['score'] += 1.0
        
        # Sort by score and return top N
        sorted_matches = sorted(matches.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Convert to dict format
        results = []
        for _, match_data in sorted_matches[:limit]:
            chunk = match_data['chunk']
            results.append({
                'file_path': chunk.file_path,
                'name': chunk.name,
                'start_line': chunk.start_line,
                'content': chunk.content,
                'score': min(match_data['score'] / 10.0, 1.0)  # Normalize to 0-1, cap at 1.0
            })
        
        return results
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from code content."""
        import re
        
        # Extract identifiers (function/variable names, class names)
        keywords = re.findall(r'\b[a-zA-Z_]\w*\b', content)
        
        # Filter out common Python/JS keywords
        common_keywords = {
            'def', 'class', 'return', 'if', 'else', 'for', 'while', 'import', 'from',
            'async', 'await', 'function', 'const', 'let', 'var', 'export', 'default',
            'this', 'self', 'true', 'false', 'null', 'undefined', 'new', 'static'
        }
        
        keywords = [k for k in keywords if k not in common_keywords and len(k) > 2]
        
        return list(set(keywords))[:20]  # Limit keywords
