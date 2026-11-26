"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Sistema de inventario de alimentos, control y gestión de mermas
-------------------------------------------------------------------------------
Autor     : Tte. Patrick Gatica F.
Curso     : I CRIM Sistema de Armas
Profesor  : Dr. Carlos Santibáñez Rodríguez
Fecha     : 26-nov-2026
Archivo   : app/main.py   →  ejecutar desde la raíz:  streamlit run app/main.py
Librerías : streamlit, supabase, pandas, altair (ver requirements.txt)

Punto de entrada: pantalla de ingreso + menú según el rol.

DECISIÓN: se usa st.navigation con una lista de páginas DISTINTA por rol.
La cocina solo tiene registradas sus 2 páginas; las páginas del administrador
ni siquiera existen para ella (no basta con ocultar un botón).
"""
import streamlit as st

st.set_page_config(page_title="Inventario de Alimentos", page_icon="🍲", layout="wide")

from core import repositorio  # noqa: E402  (después de set_page_config)
from core.auth import (  # noqa: E402
    autenticar,
    cerrar_sesion,
    iniciar_sesion,
    intentos_agotados,
    registrar_intento_fallido,
    usuario_actual,
)
from vistas import admin, cocina  # noqa: E402

ROL_ETIQUETA = {"cocina": "Perfil Cocina", "administrador": "Perfil Administrador"}


def pagina_ingreso() -> None:
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.title("🍲 Inventario de Alimentos")
        st.caption("Control de insumos y gestión de mermas — ingrese con su usuario.")
        with st.form("login"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Ingresar", type="primary")
        if not enviar:
            return
        if intentos_agotados():
            st.error("Demasiados intentos fallidos. Recargue la página para reintentar.")
            return
        try:
            usuarios = repositorio.obtener_usuarios()
        except Exception as e:  # sin conexión, tabla inexistente, clave errónea…
            st.error(f"No se pudo consultar la base de datos. Revise .streamlit/secrets.toml.\n\n{e}")
            return
        u = autenticar(usuario, clave, usuarios)
        if u:
            iniciar_sesion(u)
            st.rerun()
        registrar_intento_fallido()
        st.error("Usuario o contraseña incorrectos.")


def paginas_por_rol(rol: str) -> list:
    if rol == "cocina":
        return [
            st.Page(cocina.nueva_orden, title="Nueva orden de preparación", icon="🧾", url_path="orden"),
            st.Page(cocina.cola_preparacion, title="Cola de preparación", icon="⏳", url_path="cola"),
        ]
    return [
        st.Page(admin.resumen, title="Resumen ejecutivo", icon="📊", url_path="resumen"),
        st.Page(admin.historial, title="Historial de órdenes", icon="📋", url_path="historial"),
        st.Page(admin.mermas, title="Análisis de mermas", icon="📉", url_path="mermas"),
        st.Page(admin.catalogo, title="Consultar insumos", icon="🔎", url_path="insumos"),
        st.Page(cocina.nueva_orden, title="Nueva orden", icon="🧾", url_path="orden"),
    ]


usuario = usuario_actual()
if not usuario:
    pg = st.navigation([st.Page(pagina_ingreso, title="Ingreso", url_path="ingreso")], position="hidden")
else:
    pg = st.navigation(paginas_por_rol(usuario["rol"]))
    with st.sidebar:
        st.markdown(f"**{usuario['nombre']}**  \n{ROL_ETIQUETA[usuario['rol']]}")
        st.button("Cerrar sesión", on_click=cerrar_sesion)
pg.run()
