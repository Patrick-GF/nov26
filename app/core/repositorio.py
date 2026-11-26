"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/core/repositorio.py
Librerías : streamlit (caché), supabase (vía core.db)

Capa de acceso a datos: TODAS las consultas a Supabase están aquí.
Las vistas nunca llaman a Supabase directamente (Actividad 5 — estructura modular).

DECISIÓN: el catálogo se guarda en caché 10 min (casi no cambia) y el historial
NO se cachea, para que el administrador vea siempre las órdenes recién creadas.
"""
from __future__ import annotations

import streamlit as st

from core.db import get_client, tabla
from core.modelos import Catalogo, Orden


@st.cache_data(ttl=600, show_spinner="Cargando catálogo…")
def _filas_catalogo() -> tuple[list, list, list]:
    ing = tabla("ingredientes").select("*").order("id").execute().data
    rec = tabla("recetas").select("*").order("id").execute().data
    rel = tabla("receta_ingredientes").select("*").execute().data
    return ing, rec, rel


def cargar_catalogo() -> Catalogo:
    return Catalogo(*_filas_catalogo())


def obtener_usuarios() -> list[dict]:
    return tabla("usuarios").select("username,nombre,rol,password_hash,activo").execute().data


def guardar_orden(orden: Orden, usuario: str) -> int:
    """Guarda cabecera + detalle en UNA transacción mediante la función SQL
    registrar_orden (si algo falla, PostgreSQL deshace todo). Devuelve el id."""
    cabecera, detalle = orden.a_registro(usuario)
    respuesta = get_client().rpc("registrar_orden", {"p_orden": cabecera, "p_detalle": detalle}).execute()
    dato = respuesta.data
    # PostgREST devuelve el bigint como número; por robustez se aceptan también [n] o [{...: n}].
    if isinstance(dato, list):
        dato = dato[0]
    if isinstance(dato, dict):
        dato = next(iter(dato.values()))
    return int(dato)


def listar_ordenes() -> list[dict]:
    return tabla("ordenes").select("*").order("fecha").execute().data


def listar_detalle() -> list[dict]:
    return tabla("orden_detalle").select("*").order("orden_id").execute().data


def detalle_de_orden(orden_id: int) -> list[dict]:
    return tabla("orden_detalle").select("*").eq("orden_id", orden_id).execute().data


def ordenes_pendientes() -> list[dict]:
    """Pendientes de la más antigua a la más nueva (orden de llegada → Cola FIFO)."""
    return (tabla("ordenes").select("id,fecha,receta_nombre,comensales,usuario")
            .eq("estado", "pendiente").order("fecha").execute().data)


def marcar_preparada(orden_id: int) -> None:
    tabla("ordenes").update({"estado": "preparada"}).eq("id", orden_id).execute()
