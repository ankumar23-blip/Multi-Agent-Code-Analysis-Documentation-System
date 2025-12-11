from pydantic import BaseModel, EmailStr
from typing import Dict, Any, List, Optional
from enum import Enum

# ============ Auth & User ============

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class SignupResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: UserRole

class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str
    role: UserRole

# ============ Projects & Analysis ============

class Persona(str, Enum):
    SDE = "sde"           # Software Development Engineer
    PM = "pm"             # Product Manager
    BOTH = "both"

class ProjectCreateRequest(BaseModel):
    name: str
    repository_url: Optional[str] = None
    personas: List[Persona] = [Persona.SDE]
    description: Optional[str] = None

class ProjectCreateResponse(BaseModel):
    project_id: str
    name: str
    created_at: str
    status: str = "created"

class ProjectInfo(BaseModel):
    project_id: str
    name: str
    owner_id: str
    repository_url: Optional[str]
    personas: List[Persona]
    status: str  # created, analyzing, completed, failed
    progress: float = 0.0
    status_message: Optional[str] = None
    created_at: str
    updated_at: str
    job_id: Optional[str] = None
    error: Optional[str] = None

# ============ Analysis (Legacy) ============

class AnalysisStartRequest(BaseModel):
    repository_url: str
    options: Dict[str, Any] = {}

class AnalysisStartResponse(BaseModel):
    job_id: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    details: Dict[str, Any] = {}
