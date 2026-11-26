"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/vistas/cocina.py
Librerías : streamlit, pandas

Actividad 3 — Interfaz operativa del perfil COCINA.

  * Formulario de solicitud: menú + comensales, con validación (no nulo, no
    negativo, no cero, entero).
  * Orden de preparación: SOLO ingrediente y cantidad a utilizar.
    DECISIÓN: el perfil cocina nunca recibe costos, mermas ni pérdidas; esos
    datos solo se dibujan si el rol es 'administrador'.
  * Persistencia automática: al calcular, la orden se guarda en Supabase.
  * Pila  → "mis últimas órdenes" de la sesión (la más reciente arriba).
  * Cola  → órdenes pendientes atendidas por orden de llegada (FIFO).
"""
import pandas as pd
import streamlit as st

from core import repositorio
from core.auth import exigir_rol
from core.calculo import calcular_orden, formato_pesos, validar_comensales
from core.estructuras import Cola, Pila
from core.modelos import Orden, texto_cantidad


# ---------------------------------------------------------------------------
# Página 1: nueva orden
# ---------------------------------------------------------------------------
def nueva_orden() -> None:
    usuario = exigir_rol("cocina", "administrador")
    st.title("🧾 Nueva orden de preparación")

    catalogo = repositorio.cargar_catalogo()
    nombres_menu = [r.nombre for r in catalogo.recetas]

    with st.form("form_orden"):
        menu = st.selectbox("Tipo de menú", nombres_menu, index=None, placeholder="Seleccione un menú…")
        # Sin min_value a propósito: la validación la hace validar_comensales()
        # y así se demuestra el control de nulos, negativos y cero.
        comensales = st.number_input("Cantidad de comensales", value=None, step=1,
                                     placeholder="Ej: 25")
        enviar = st.form_submit_button("Calcular y registrar orden", type="primary")

    if enviar:
        errores = []
        if menu is None:
            errores.append("Debe seleccionar un tipo de menú.")
        try:
            n = validar_comensales(comensales)
        except ValueError as e:
            errores.append(str(e))
        if errores:
            for err in errores:
                st.error(err)
        else:
            receta = catalogo.buscar_receta(menu)          # búsqueda secuencial
            orden = calcular_orden(receta, n)               # motor (core/calculo.py)
            try:
                orden_id = repositorio.guardar_orden(orden, usuario["username"])
            except Exception as e:
                st.error(f"No se pudo registrar la orden en la base de datos: {e}")
                return
            st.session_state["ultima_orden"] = (orden_id, orden)
            # Pila de la sesión: la última orden registrada queda en el tope.
            pila: Pila = st.session_state.setdefault("pila_ordenes", Pila())
            pila.apilar((orden_id, orden.receta.nombre, orden.comensales))

    if "ultima_orden" in st.session_state:
        orden_id, orden = st.session_state["ultima_orden"]
        _mostrar_orden(orden_id, orden, es_admin=usuario["rol"] == "administrador")

    pila = st.session_state.get("pila_ordenes")
    if pila and len(pila) > 0:
        with st.expander(f"Mis últimas órdenes de esta sesión ({len(pila)})"):
            for oid, nombre, n in pila:                     # recorre del tope al fondo
                st.write(f"N° {oid} — {nombre} — {n} comensales")


def _mostrar_orden(orden_id: int, orden: Orden, es_admin: bool) -> None:
    st.success(f"Orden N° {orden_id} registrada correctamente.")
    st.subheader(f"{orden.receta.nombre} — {orden.comensales} comensales")

    # Lo único que ve la cocina: qué ingrediente y cuánto usar.
    tabla_cocina = pd.DataFrame(
        [{"Ingrediente": l.ingrediente.nombre, "Cantidad a utilizar": l.cantidad_texto}
         for l in orden.lineas]
    )
    st.table(tabla_cocina)

    if not es_admin:
        return

    # ----- Solo administrador: datos económicos de la orden recién creada -----
    st.markdown("##### Datos económicos (solo administrador)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo total", formato_pesos(orden.costo_total))
    c2.metric("Costo por plato", formato_pesos(orden.costo_por_plato))
    c3.metric("Precio venta por plato (+25 %)", formato_pesos(orden.precio_venta_plato))
    c4.metric("Pérdida por merma", formato_pesos(orden.perdida_total))
    st.dataframe(pd.DataFrame([
        {"Ingrediente": l.ingrediente.nombre,
         "Envases": l.envases,
         "Costo envase": formato_pesos(l.ingrediente.costo_envase),
         "Costo línea": formato_pesos(l.costo_linea),
         "Porciones sobrantes": l.porciones_sobrantes,
         "Merma (fracción envase)": round(l.merma_envase, 3),
         "Pérdida": formato_pesos(l.perdida)}
        for l in orden.lineas
    ]), hide_index=True)


# ---------------------------------------------------------------------------
# Página 2: cola de preparación (FIFO)
# ---------------------------------------------------------------------------
def cola_preparacion() -> None:
    exigir_rol("cocina", "administrador")
    st.title("⏳ Cola de preparación")
    st.caption("Las órdenes se atienden por orden de llegada (FIFO): la primera que entró es la primera que se prepara.")

    cola = Cola()
    for fila in repositorio.ordenes_pendientes():          # ya vienen ordenadas por fecha
        cola.encolar(fila)

    if cola.esta_vacia():
        st.info("No hay órdenes pendientes.")
        return

    frente = cola.frente()
    st.subheader(f"Siguiente: N° {frente['id']} — {frente['receta_nombre']} ({frente['comensales']} comensales)")
    detalle = repositorio.detalle_de_orden(frente["id"])
    st.table(pd.DataFrame([
        {"Ingrediente": d["ingrediente_nombre"],
         "Cantidad a utilizar": texto_cantidad(d["envases"], d["unidad_compra"])}
        for d in detalle
    ]))
    if st.button("✅ Marcar como preparada", type="primary"):
        atendida = cola.desencolar()
        repositorio.marcar_preparada(atendida["id"])
        st.rerun()

    if len(cola) > 1:
        st.markdown(f"**En espera ({len(cola) - 1})**")
        en_espera = list(cola)[1:]
        st.dataframe(pd.DataFrame([
            {"N°": f["id"], "Menú": f["receta_nombre"], "Comensales": f["comensales"],
             "Hora": pd.to_datetime(f["fecha"]).tz_convert("America/Santiago").strftime("%d-%m %H:%M")}
            for f in en_espera
        ]), hide_index=True)
