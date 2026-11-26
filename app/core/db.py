"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/core/db.py
Librerías : streamlit, supabase

Conexión a Supabase (Actividad 5 — Manejo seguro de credenciales).

DECISIÓN: la URL y la clave se leen SOLO desde st.secrets, que Streamlit carga
desde .streamlit/secrets.toml (archivo ignorado por git) o desde Settings →
Secrets en Streamlit Cloud. En el código fuente no aparece ninguna llave.
Se usa la clave *publishable* (rol anon), cuyos permisos limita el RLS de la BD.
"""
import streamlit as st
from supabase import Client, create_client


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    """Crea el cliente una sola vez por servidor (st.cache_resource) y lo reutiliza."""
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["key"])


def tabla(nombre: str):
    return get_client().table(nombre)
