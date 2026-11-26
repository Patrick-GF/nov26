"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/core/seguridad.py
Librerías : hashlib, hmac, secrets, base64 (estándar)

Hash de contraseñas con PBKDF2-HMAC-SHA256 + sal aleatoria.

DECISIÓN: módulo separado y SIN streamlit, para que lo use tanto la app
(core/auth.py) como el script que crea los usuarios (scripts/crear_usuarios.py).
¿Por qué PBKDF2? Aplica SHA-256 200.000 veces: verificar 1 clave es instantáneo,
pero probar millones de claves por fuerza bruta se vuelve muy lento. La sal
(16 bytes al azar) hace que dos usuarios con la misma clave tengan hashes distintos.
"""
import base64
import hashlib
import hmac
import secrets

ITERACIONES = 200_000


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    """Formato guardado: pbkdf2_sha256$iteraciones$sal_base64$hash_base64"""
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${_b64(sal)}${_b64(dk)}"


def verify_password(password: str, almacenado: str) -> bool:
    try:
        _, iters, sal, dk = almacenado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(sal), int(iters))
        # compare_digest compara en tiempo constante (no filtra información por el tiempo).
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False
