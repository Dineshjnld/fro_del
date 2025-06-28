"""
Authentication middleware for CCTNS API
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import logging
from typing import Optional
from datetime import datetime, timedelta
from config.settings import settings

security = HTTPBearer()
logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication middleware for API endpoints"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.token_expire_hours = 24
    
    def create_access_token(self, user_data: dict) -> str:
        """Create JWT access token"""
        try:
            expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
            payload = {
                **user_data,
                "exp": expire,
                "iat": datetime.utcnow(),
                "iss": "cctns-copilot"
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
            
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise HTTPException(status_code=500, detail="Token creation failed")
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
        """Verify JWT token"""
        try:
            token = credentials.credentials
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            if datetime.fromtimestamp(payload.get("exp", 0)) < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Token expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    def get_current_user(self, token_data: dict = Depends(verify_token)) -> dict:
        """Get current user from token"""
        return {
            "user_id": token_data.get("user_id"),
            "username": token_data.get("username"),
            "role": token_data.get("role", "user"),
            "permissions": token_data.get("permissions", [])
        }
    
    def require_role(self, required_role: str):
        """Decorator to require specific role"""
        def role_checker(current_user: dict = Depends(self.get_current_user)):
            if current_user.get("role") != required_role:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Role '{required_role}' required"
                )
            return current_user
        return role_checker
    
    def require_permission(self, required_permission: str):
        """Decorator to require specific permission"""
        def permission_checker(current_user: dict = Depends(self.get_current_user)):
            permissions = current_user.get("permissions", [])
            if required_permission not in permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{required_permission}' required"
                )
            return current_user
        return permission_checker

# Global auth instance
auth = AuthMiddleware()

# Convenience functions
def get_current_user() -> dict:
    """Get current authenticated user"""
    return Depends(auth.get_current_user)

def require_admin():
    """Require admin role"""
    return Depends(auth.require_role("admin"))

def require_officer():
    """Require officer role"""
    return Depends(auth.require_role("officer"))