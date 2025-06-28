"""
Security middleware for CCTNS API
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
import logging
from typing import Dict, Set
from collections import defaultdict, deque
import hashlib
import ipaddress

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Security middleware for API protection"""
    
    def __init__(self):
        # Rate limiting
        self.rate_limit_requests = defaultdict(deque)
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 100
        
        # IP blocking
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips = defaultdict(int)
        
        # Request tracking
        self.request_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "rate_limited_requests": 0
        }
    
    async def __call__(self, request: Request, call_next):
        """Main middleware function"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        self.request_stats["total_requests"] += 1
        
        try:
            # Security checks
            security_check = await self._perform_security_checks(request, client_ip)
            if not security_check["allowed"]:
                self.request_stats["blocked_requests"] += 1
                return JSONResponse(
                    status_code=security_check["status_code"],
                    content={"error": security_check["message"]}
                )
            
            # Rate limiting
            if not self._check_rate_limit(client_ip):
                self.request_stats["rate_limited_requests"] += 1
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after": self.rate_limit_window
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Log request
            processing_time = time.time() - start_time
            await self._log_request(request, response, client_ip, processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            self.request_stats["blocked_requests"] += 1
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )
    
    async def _perform_security_checks(self, request: Request, client_ip: str) -> Dict:
        """Perform various security checks"""
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            return {
                "allowed": False,
                "status_code": 403,
                "message": "IP address blocked"
            }
        
        # Check for suspicious patterns
        if self._is_suspicious_request(request):
            self.suspicious_ips[client_ip] += 1
            if self.suspicious_ips[client_ip] > 10:
                self.blocked_ips.add(client_ip)
                logger.warning(f"🚫 Blocked suspicious IP: {client_ip}")
            
            return {
                "allowed": False,
                "status_code": 400,
                "message": "Suspicious request pattern detected"
            }
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB
            return {
                "allowed": False,
                "status_code": 413,
                "message": "Request too large"
            }
        
        # Check User-Agent
        user_agent = request.headers.get("user-agent", "")
        if self._is_suspicious_user_agent(user_agent):
            return {
                "allowed": False,
                "status_code": 403,
                "message": "Suspicious user agent"
            }
        
        return {"allowed": True}
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if request is within rate limits"""
        now = time.time()
        
        # Clean old requests
        requests = self.rate_limit_requests[client_ip]
        while requests and requests[0] < now - self.rate_limit_window:
            requests.popleft()
        
        # Check if under limit
        if len(requests) >= self.rate_limit_max_requests:
            return False
        
        # Add current request
        requests.append(now)
        return True
    
    def _is_suspicious_request(self, request: Request) -> bool:
        """Check for suspicious request patterns"""
        path = str(request.url.path).lower()
        query = str(request.url.query).lower()
        
        # SQL injection patterns
        sql_patterns = [
            "union select", "drop table", "insert into", "update set",
            "delete from", "create table", "alter table", "--", "/*",
            "xp_cmdshell", "sp_executesql"
        ]
        
        # XSS patterns
        xss_patterns = [
            "<script", "javascript:", "onerror=", "onload=",
            "alert(", "confirm(", "prompt("
        ]
        
        # Path traversal patterns
        traversal_patterns = [
            "../", "..\\", "..", "\\x2e\\x2e", "%2e%2e"
        ]
        
        # Check all patterns
        all_patterns = sql_patterns + xss_patterns + traversal_patterns
        content = path + " " + query
        
        for pattern in all_patterns:
            if pattern in content:
                logger.warning(f"🚨 Suspicious pattern detected: {pattern} in {request.url}")
                return True
        
        return False
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check for suspicious user agents"""
        suspicious_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap", "burp",
            "python-requests", "curl", "wget", "scanner"
        ]
        
        user_agent_lower = user_agent.lower()
        return any(agent in user_agent_lower for agent in suspicious_agents)
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    async def _log_request(self, request: Request, response, client_ip: str, processing_time: float):
        """Log request details"""
        log_data = {
            "ip": client_ip,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "processing_time": round(processing_time, 3),
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": time.time()
        }
        
        # Log based on status
        if response.status_code >= 400:
            logger.warning(f"🚨 HTTP {response.status_code}: {log_data}")
        else:
            logger.info(f"✅ Request: {log_data}")
    
    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        return {
            **self.request_stats,
            "blocked_ips": len(self.blocked_ips),
            "suspicious_ips": len(self.suspicious_ips),
            "rate_limited_ips": len(self.rate_limit_requests)
        }
    
    def block_ip(self, ip_address: str, reason: str = "Manual block"):
        """Manually block an IP address"""
        try:
            # Validate IP address
            ipaddress.ip_address(ip_address)
            self.blocked_ips.add(ip_address)
            logger.info(f"🚫 Manually blocked IP {ip_address}: {reason}")
        except ValueError:
            logger.error(f"❌ Invalid IP address: {ip_address}")
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            logger.info(f"✅ Unblocked IP: {ip_address}")
        
        if ip_address in self.suspicious_ips:
            del self.suspicious_ips[ip_address]
    
    def clear_rate_limits(self):
        """Clear all rate limit counters"""
        self.rate_limit_requests.clear()
        logger.info("🧹 Rate limit counters cleared")

# Global security middleware instance
security_middleware = SecurityMiddleware()