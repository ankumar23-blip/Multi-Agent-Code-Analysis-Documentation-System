"""File validation and repository utilities."""
import re
import httpx
from typing import Tuple

# File size limit: 100 MB
MAX_FILE_SIZE = 100 * 1024 * 1024


def validate_github_url(url: str) -> Tuple[bool, str]:
    """Validate a GitHub URL format and check if repository is accessible.
    
    Returns: (is_valid, error_message or '')
    """
    # GitHub URL patterns
    github_patterns = [
        r'^https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+/?$',
        r'^git@github\.com:[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+\.git$',
    ]
    
    url = url.strip()
    
    # Check format
    is_valid_format = any(re.match(pattern, url) for pattern in github_patterns)
    if not is_valid_format:
        return False, "Invalid GitHub URL format. Use: https://github.com/owner/repo"
    
    # Try to access the repository (basic check)
    try:
        # Convert SSH to HTTPS if needed
        if url.startswith('git@'):
            url = url.replace('git@github.com:', 'https://github.com/').replace('.git', '')
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Check if repo exists by accessing the API
        api_url = url.replace('https://github.com/', 'https://api.github.com/repos/')
        
        resp = httpx.head(api_url, timeout=5, follow_redirects=True)
        
        if resp.status_code == 404:
            return False, "GitHub repository not found (may be private or deleted)"
        elif resp.status_code == 401:
            return False, "GitHub repository is private (requires authentication)"
        elif resp.status_code >= 400:
            return False, f"Unable to access repository (HTTP {resp.status_code})"
        
        return True, ""
    
    except httpx.TimeoutException:
        return False, "Timeout connecting to GitHub (check your internet connection)"
    except httpx.RequestError as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_zip_file(file_path: str, file_size: int) -> Tuple[bool, str]:
    """Validate a ZIP file.
    
    Returns: (is_valid, error_message or '')
    """
    import zipfile
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: 100MB, received: {file_size / (1024*1024):.1f}MB"
    
    # Check file extension
    if not file_path.lower().endswith('.zip'):
        return False, "Invalid file format. Only .zip files are supported"
    
    try:
        # Try to open and validate ZIP - just check it's valid
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Check if ZIP is corrupted
            bad_file = zf.testzip()
            if bad_file:
                return False, f"ZIP file is corrupted. Bad file: {bad_file}"
            
            # Check if ZIP is empty
            files = zf.namelist()
            if len(files) == 0:
                return False, "ZIP file is empty"
            
            # Accept if it has any files at all (very permissive)
            return True, ""
    
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file format or file is corrupted"
    except Exception as e:
        return False, f"ZIP validation error: {str(e)}"


def extract_repo_owner_and_name(github_url: str) -> Tuple[str, str]:
    """Extract owner and repo name from GitHub URL.
    
    Returns: (owner, repo_name)
    """
    url = github_url.strip().rstrip('/')
    
    # Handle HTTPS format
    if 'github.com/' in url:
        parts = url.split('github.com/')[-1].split('/')
        return parts[0], parts[1]
    
    # Handle SSH format
    if 'git@github.com:' in url:
        parts = url.split(':')[-1].replace('.git', '').split('/')
        return parts[0], parts[1]
    
    return '', ''
