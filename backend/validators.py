from __future__ import annotations

import ipaddress
import os
import re
import socket
import urllib.parse
from typing import Optional, Tuple

from .logging_config import get_logger

logger = get_logger("validators")

_ENV = os.getenv("ENVIRONMENT", "development").strip().lower()
_IS_DEV = _ENV in {"development", "dev", "test", "testing"}

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,63}$"
)

_BAD_EMAIL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\.{2,}"),     
    re.compile(r"^[.\-@]"),    
    re.compile(r"[.\-]@"),     
    re.compile(r"@[.\-]"),    
    re.compile(r"[.\-]$"),   
]


def validate_email(raw: str) -> Tuple[bool, str]:
    if not raw or not isinstance(raw, str):
        return False, "Email must be a non-empty string"

    email = raw.strip().lower()

    if len(email) > 254:            
        return False, "Email address exceeds the 254-character RFC limit"

    if not _EMAIL_RE.match(email):
        return False, "Email address format is invalid"

    for pattern in _BAD_EMAIL_PATTERNS:
        if pattern.search(email):
            return False, "Email address contains an invalid character sequence"

    local, domain = email.rsplit("@", 1)
    if len(local) > 64:           
        return False, "Email local part exceeds the 64-character RFC limit"

    if "." not in domain:
        return False, "Email domain must contain at least one dot"

    return True, email


_SEQUENTIAL_PATTERNS = re.compile(
    r"(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|"
    r"qwe|wer|ert|rty|tyu|yui|asd|sdf|dfg|zxc|xcv|cvb|vbn)",
    re.IGNORECASE,
)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    if not isinstance(password, str):
        return False, "Password must be a string"
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if len(password) > 128:
        return False, "Password must be at most 128 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A–Z)"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a–z)"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit (0–9)"
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:',.<>?/`~\\]", password):
        return False, "Password must contain at least one special character"
    if re.match(r"^(.)\1{7,}$", password):
        return False, "Password cannot consist of a single repeated character"
    if _SEQUENTIAL_PATTERNS.search(password):
        return False, "Password contains a common sequential pattern"

    return True, "OK"


_PRIVATE_NETWORKS: list[ipaddress._BaseNetwork] = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),      
    ipaddress.ip_network("169.254.0.0/16"),   
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    
    ipaddress.ip_network("240.0.0.0/4"),      
    ipaddress.ip_network("::1/128"),           
    ipaddress.ip_network("fc00::/7"),          
    ipaddress.ip_network("fe80::/10"),      
]

_ALLOWED_SCHEMES = {"http", "https"}


def validate_ollama_url(url: str) -> Tuple[bool, str]:
    if not url:
        return True, "No Ollama URL configured"

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, f"Malformed Ollama URL: {url!r}"

    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False, (
            f"Scheme '{parsed.scheme}' is not permitted in OLLAMA_URL. "
            "Only 'http' and 'https' are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        return False, "OLLAMA_URL must include a hostname"

    if any(c in hostname for c in ("%", "\\", "..", "@")):
        return False, f"OLLAMA_URL hostname '{hostname}' contains suspicious characters"

    try:
        ip_str = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip_str)
    except socket.gaierror:
        if _IS_DEV:
            logger.warning("validators.ollama_dns_skip", hostname=hostname, env=_ENV)
            return True, "DNS resolution skipped in development"
        return False, f"Cannot resolve OLLAMA_URL hostname '{hostname}'"

    for network in _PRIVATE_NETWORKS:
        if ip_addr in network:
            if str(ip_addr) in {"127.0.0.1", "::1"} and _IS_DEV:
                return True, "Localhost Ollama URL accepted in development"
            return False, (
                f"SSRF risk: '{hostname}' resolves to private/reserved address "
                f"'{ip_addr}'. Only public Ollama endpoints are permitted."
            )

    return True, f"URL accepted (resolved to {ip_addr})"


def validate_ollama_url_from_env() -> None:
    url = os.getenv("OLLAMA_URL", "").strip()
    if not url:
        return
    valid, message = validate_ollama_url(url)
    if not valid:
        raise RuntimeError(
            f"OLLAMA_URL rejected: {message}. "
            "Fix or unset OLLAMA_URL before starting the server."
        )
    logger.info(
        "validators.ollama_url_ok",
        host=urllib.parse.urlparse(url).hostname,
    )


MAX_CHAT_MESSAGE_LEN = int(os.getenv("MAX_CHAT_MESSAGE_LENGTH", "2000"))

_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|context)",
    r"you\s+are\s+now\s+(?:a\s+)?(?:dan|evil|unfiltered|uncensored|jailbreak)",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:an?\s+)?(?:evil|unfiltered|uncensored)",
    r"<\|?(?:im_start|im_end|endoftext|pad)\|?>",
    r"\[INST\]|\[/INST\]|\[SYS\]|\[/SYS\]",
    r"###\s*(?:Human|Assistant|System|User)\s*:",
    r"<<SYS>>|<</SYS>>",
    r"\{\{.*?\}\}",
    r"\{%.*?%\}",
    r"<!--.*?-->",
    r"```(?:bash|sh|python|js)\s+(?:cat|curl|wget|nc|ncat|python|node)",
    r"^(?:system|developer|admin|root)\s*:\s*",
]
_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL
)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitise_chat_message(message: str) -> Tuple[bool, str]:
    if not message or not isinstance(message, str):
        return False, "Message must be a non-empty string"

    if len(message) > MAX_CHAT_MESSAGE_LEN:
        return False, (
            f"Message is too long ({len(message)} characters). "
            f"Maximum allowed is {MAX_CHAT_MESSAGE_LEN} characters."
        )

    cleaned = _CONTROL_CHARS_RE.sub("", message)

    match = _INJECTION_RE.search(cleaned)
    if match:
        logger.warning(
            "validators.prompt_injection_blocked",
            pattern_matched=match.group(0)[:60],
        )
        return False, (
            "Your message contains patterns that cannot be processed. "
            "Please rephrase your eye-health question."
        )

    return True, cleaned.strip()


ALLOWED_ROLES = frozenset({"patient", "clinician", "admin"})


def validate_role_claim(role: Optional[str]) -> Tuple[bool, str]:
    if not role or role not in ALLOWED_ROLES:
        return False, f"Unknown or missing role claim: '{role}'"
    return True, role
