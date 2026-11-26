"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/core/auth.py
Librerías : hashlib (estándar), streamlit

Autenticación y control de acceso por rol (Actividad 3 — Control de acceso;
Indicador IE5 — búsqueda secuencial para validar accesos).

Flujo:
  1. Se leen los usuarios de la tabla 'usuarios' (Supabase).
  2. BÚSQUEDA SECUENCIAL del username en esa lista.
  3. Se verifica la contraseña contra su hash PBKDF2-SHA256 (nunca texto plano).
  4. El usuario queda en st.session_state y main.py arma el menú según su rol:
     la cocina NO tiene registradas las páginas del administrador.
  5. exigir_rol() se llama al inicio de cada vista (defensa en profundidad).
"""
from __future__ import annotations

import hashlib

import streamlit as st

from core.ordenamiento import busqueda_secuencial
from core.seguridad import ITERACIONES, verify_password

MAX_INTENTOS = 5


# ------------------------------- Autenticación -------------------------------
def autenticar(username: str, password: str, usuarios: list[dict]) -> dict | None:
    """Devuelve {username, nombre, rol} si las credenciales son válidas; si no, None.
    'usuarios' viene de repositorio.obtener_usuarios() (se pasa como parámetro para
    poder probar esta función sin conexión)."""
    u = (username or "").strip().lower()
    if not u or not password:
        return None
    fila = busqueda_secuencial(usuarios, lambda r: r["username"].lower() == u and r["activo"])
    if fila is None:
        # Se calcula un hash igual para no revelar por el tiempo de respuesta si el usuario existe.
        hashlib.pbkdf2_hmac("sha256", password.encode(), b"x" * 16, ITERACIONES)
        return None
    if not verify_password(password, fila["password_hash"]):
        return None
    return {"username": fila["username"], "nombre": fila["nombre"], "rol": fila["rol"]}


# ---------------------------------- Sesión -----------------------------------
def intentos_agotados() -> bool:
    return st.session_state.get("intentos_fallidos", 0) >= MAX_INTENTOS


def registrar_intento_fallido() -> None:
    st.session_state["intentos_fallidos"] = st.session_state.get("intentos_fallidos", 0) + 1


def iniciar_sesion(usuario: dict) -> None:
    st.session_state["usuario"] = usuario
    st.session_state["intentos_fallidos"] = 0


def cerrar_sesion() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def usuario_actual() -> dict | None:
    return st.session_state.get("usuario")


def exigir_rol(*roles: str) -> dict:
    """Si el rol de la sesión no está permitido, muestra error y detiene la página."""
    u = usuario_actual()
    if not u or u["rol"] not in roles:
        st.error("No tienes permisos para ver esta sección.")
        st.stop()
    return u
