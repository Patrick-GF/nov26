"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : app/vistas/admin.py
Librerías : streamlit, pandas, altair

Actividad 4 — Panel de control gerencial del perfil ADMINISTRADOR.

  Página              Contenido                                   Estructura / algoritmo
  ------------------  ------------------------------------------  --------------------------------
  Resumen ejecutivo   KPIs globales                               Cola con prioridad (menú crítico)
  Historial           tabla filtrable + desglose + exportación    búsqueda secuencial, merge sort,
                                                                  ordenamiento externo
  Análisis de mermas  pérdida por menú / ingrediente, top 10,     cola con prioridad, árbol binario
                      simulador de comensales
  Consultar insumos   buscador de ingredientes y recetas          búsqueda secuencial, grafo
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from core import repositorio
from core.auth import exigir_rol
from core.calculo import calcular_orden, formato_pesos
from core.estructuras import ArbolBinarioBusqueda, ColaPrioridad
from core.ordenamiento import busqueda_secuencial_todos, merge_sort, ordenamiento_externo

ZONA = "America/Santiago"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _ordenes() -> list[dict]:
    """Órdenes con los montos convertidos a float (Supabase entrega numeric)."""
    filas = repositorio.listar_ordenes()
    for f in filas:
        for c in ("costo_total", "costo_por_plato", "precio_venta_plato", "ingreso_proyectado", "perdida_merma"):
            f[c] = float(f[c])
    return filas


def _detalle() -> list[dict]:
    filas = repositorio.listar_detalle()
    for f in filas:
        for c in ("merma_envase", "costo_linea", "perdida"):
            f[c] = float(f[c])
    return filas


def _fecha_local(iso: str) -> str:
    return pd.to_datetime(iso).tz_convert(ZONA).strftime("%d-%m-%Y %H:%M")


def _agrupar(filas: list[dict], campo_grupo: str, campos_suma: list[str]) -> dict[str, dict]:
    """Agrupa con un diccionario: {grupo: {'n': cantidad, campo: suma, …}}."""
    grupos: dict[str, dict] = {}
    for f in filas:
        g = grupos.setdefault(f[campo_grupo], {"n": 0, **{c: 0.0 for c in campos_suma}})
        g["n"] += 1
        for c in campos_suma:
            g[c] += f[c]
    return grupos


def _barras(df: pd.DataFrame, x: str, y: str, titulo_x: str) -> alt.Chart:
    """Barras horizontales ordenadas de mayor a menor."""
    return (alt.Chart(df).mark_bar()
            .encode(x=alt.X(f"{x}:Q", title=titulo_x),
                    y=alt.Y(f"{y}:N", sort="-x", title=None),
                    tooltip=list(df.columns))
            .properties(height=max(160, 32 * len(df))))


# ---------------------------------------------------------------------------
# Página 1: Resumen ejecutivo (KPIs)
# ---------------------------------------------------------------------------
def resumen() -> None:
    exigir_rol("administrador")
    st.title("📊 Resumen ejecutivo")
    ordenes = _ordenes()
    if not ordenes:
        st.info("Aún no hay órdenes registradas.")
        return

    costo = sum(o["costo_total"] for o in ordenes)
    perdida = sum(o["perdida_merma"] for o in ordenes)
    ingresos = sum(o["ingreso_proyectado"] for o in ordenes)
    comensales = sum(o["comensales"] for o in ordenes)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Servicios realizados", len(ordenes), help=f"{comensales} comensales en total")
    c2.metric("Costo total de operación", formato_pesos(costo))
    c3.metric("Pérdida total por merma", formato_pesos(perdida),
              help=f"{perdida / costo:.1%} del costo total")
    c4.metric("Ingresos proyectados por venta", formato_pesos(ingresos),
              help=f"Ganancia proyectada: {formato_pesos(ingresos - costo)}")

    # Cola con prioridad: el menú con mayor pérdida acumulada sale primero.
    grupos = _agrupar(ordenes, "receta_nombre", ["perdida_merma"])
    cp = ColaPrioridad()
    for menu, g in grupos.items():
        cp.insertar(menu, g["perdida_merma"])
    menu_critico, monto = cp.extraer_max()
    st.warning(f"Menú con mayor pérdida acumulada: **{menu_critico}** ({formato_pesos(monto)}).")

    st.markdown("##### Costo vs pérdida por día")
    df = pd.DataFrame(ordenes)
    df["dia"] = pd.to_datetime(df["fecha"]).dt.tz_convert(ZONA).dt.date.astype(str)
    por_dia = df.groupby("dia")[["costo_total", "perdida_merma"]].sum()
    por_dia.columns = ["Costo", "Pérdida"]
    st.bar_chart(por_dia)


# ---------------------------------------------------------------------------
# Página 2: Historial filtrable y ordenable
# ---------------------------------------------------------------------------
COLUMNAS_ORDEN = {
    "Fecha": "fecha",
    "Comensales": "comensales",
    "Costo por plato": "costo_por_plato",
    "Pérdida por merma": "perdida_merma",
    "Valor de venta por plato": "precio_venta_plato",
    "Merma física (porciones)": "merma_porciones",
}


def historial() -> None:
    exigir_rol("administrador")
    st.title("📋 Historial de órdenes")
    ordenes = _ordenes()
    if not ordenes:
        st.info("Aún no hay órdenes registradas.")
        return
    detalle = _detalle()

    # Merma física total por orden (suma de porciones sobrantes de su detalle).
    merma_por_orden = _agrupar(detalle, "orden_id", ["porciones_sobrantes"])
    for o in ordenes:
        o["merma_porciones"] = int(merma_por_orden.get(o["id"], {}).get("porciones_sobrantes", 0))

    # ---- Filtros (búsqueda secuencial sobre la lista de órdenes) ----
    menus = sorted({o["receta_nombre"] for o in ordenes})
    f1, f2, f3 = st.columns([3, 2, 1])
    elegidos = f1.multiselect("Filtrar por tipo de menú", menus, placeholder="Todos los menús")
    criterio = f2.selectbox("Ordenar por", list(COLUMNAS_ORDEN), index=3)
    desc = f3.radio("Sentido", ["Mayor a menor", "Menor a mayor"]) == "Mayor a menor"

    filtradas = busqueda_secuencial_todos(ordenes, lambda o: not elegidos or o["receta_nombre"] in elegidos)
    # ---- Ordenamiento interno: Merge Sort (estable) ----
    campo = COLUMNAS_ORDEN[criterio]
    filtradas = merge_sort(filtradas, clave=lambda o: o[campo], descendente=desc)

    st.caption(f"{len(filtradas)} órdenes — ordenadas con Merge Sort por «{criterio}».")
    st.dataframe(pd.DataFrame([
        {"N°": o["id"], "Fecha": _fecha_local(o["fecha"]), "Menú": o["receta_nombre"],
         "Comensales": o["comensales"], "Costo total": formato_pesos(o["costo_total"]),
         "Costo por plato": formato_pesos(o["costo_por_plato"]),
         "Merma física (porciones)": o["merma_porciones"],
         "Pérdida por merma": formato_pesos(o["perdida_merma"]),
         "Valor de venta por plato": formato_pesos(o["precio_venta_plato"]),
         "Ingreso proyectado": formato_pesos(o["ingreso_proyectado"]),
         "Estado": o["estado"]}
        for o in filtradas
    ]), hide_index=True)

    # ---- Desglose completo de una orden ----
    st.markdown("##### Desglose de una orden")
    ids = [o["id"] for o in filtradas]
    if ids:
        oid = st.selectbox("N° de orden", ids)
        filas = busqueda_secuencial_todos(detalle, lambda d: d["orden_id"] == oid)
        st.dataframe(pd.DataFrame([
            {"Ingrediente": d["ingrediente_nombre"], "Unidad de compra": d["unidad_compra"],
             "Rinde (personas)": d["personas_por_envase"], "Porciones requeridas": d["porciones_requeridas"],
             "Envases usados": d["envases"], "Costo envase": formato_pesos(d["costo_envase"]),
             "Costo línea": formato_pesos(d["costo_linea"]),
             "Merma física (porciones)": d["porciones_sobrantes"],
             "Merma (fracción envase)": round(d["merma_envase"], 3),
             "Pérdida": formato_pesos(d["perdida"])}
            for d in filas
        ]), hide_index=True)

    # ---- Ordenamiento externo: exportar por bloques ----
    st.markdown("##### Exportar historial (ordenamiento externo)")
    st.caption("Divide el historial en bloques, ordena cada bloque en memoria, lo guarda en un "
               "archivo temporal y luego mezcla los archivos (merge sort externo de k vías).")
    tam = st.number_input("Tamaño de bloque (registros por archivo temporal)", min_value=1, value=5, step=1)
    if st.button("Generar CSV ordenado por pérdida (mayor a menor)"):
        ordenados, n_runs = ordenamiento_externo(filtradas, clave=lambda o: o["perdida_merma"],
                                                 tam_bloque=int(tam), descendente=True)
        st.success(f"Listo: {len(ordenados)} registros, {n_runs} bloques temporales mezclados.")
        csv = pd.DataFrame(ordenados).to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar CSV", csv, file_name="historial_por_perdida.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# Página 3: Análisis de desechos e impacto económico
# ---------------------------------------------------------------------------
def mermas() -> None:
    exigir_rol("administrador")
    st.title("📉 Análisis de mermas e impacto económico")
    ordenes = _ordenes()
    if not ordenes:
        st.info("Aún no hay órdenes registradas.")
        return
    detalle = _detalle()

    col1, col2 = st.columns(2)

    # ---- Pérdida por menú (ranking con Cola con Prioridad) ----
    with col1:
        st.markdown("##### Pérdida acumulada por menú")
        grupos = _agrupar(ordenes, "receta_nombre", ["perdida_merma", "costo_total"])
        cp = ColaPrioridad()
        for menu, g in grupos.items():
            cp.insertar((menu, g), g["perdida_merma"])
        ranking = []
        while not cp.esta_vacia():
            (menu, g), _ = cp.extraer_max()
            ranking.append({"menu": menu, "perdida": g["perdida_merma"], "servicios": g["n"],
                            "pct_costo": round(100 * g["perdida_merma"] / g["costo_total"], 1)})
        st.altair_chart(_barras(pd.DataFrame(ranking), "perdida", "menu", "Pérdida ($)"))
        st.dataframe(pd.DataFrame([
            {"#": i + 1, "Menú": r["menu"], "Servicios": r["servicios"],
             "Pérdida": formato_pesos(r["perdida"]), "% del costo": r["pct_costo"]}
            for i, r in enumerate(ranking)
        ]), hide_index=True)

    # ---- Pérdida por ingrediente ----
    with col2:
        st.markdown("##### Pérdida acumulada por ingrediente")
        g_ing = _agrupar(detalle, "ingrediente_nombre", ["perdida", "porciones_sobrantes", "merma_envase"])
        filas = merge_sort(
            [{"ingrediente": k, "perdida": v["perdida"], "porciones": int(v["porciones_sobrantes"]),
              "envases": round(v["merma_envase"], 2)} for k, v in g_ing.items()],
            clave=lambda r: r["perdida"], descendente=True)
        st.altair_chart(_barras(pd.DataFrame(filas), "perdida", "ingrediente", "Pérdida ($)"))
        st.dataframe(pd.DataFrame([
            {"Ingrediente": r["ingrediente"], "Pérdida": formato_pesos(r["perdida"]),
             "Porciones desechadas": r["porciones"], "Envases desechados (equiv.)": r["envases"]}
            for r in filas
        ]), hide_index=True)

    # ---- Top 10 órdenes con mayor pérdida (Árbol Binario de Búsqueda) ----
    st.markdown("##### Top 10 órdenes con mayor pérdida")
    abb = ArbolBinarioBusqueda()
    for o in ordenes:
        abb.insertar(o["perdida_merma"], o)
    top = abb.inorden(descendente=True)[:10]
    st.caption(f"Árbol binario de búsqueda con {len(abb)} nodos (altura {abb.altura()}), "
               "recorrido en orden inverso (derecha → raíz → izquierda).")
    st.dataframe(pd.DataFrame([
        {"N°": o["id"], "Fecha": _fecha_local(o["fecha"]), "Menú": o["receta_nombre"],
         "Comensales": o["comensales"], "Pérdida": formato_pesos(clave)}
        for clave, o in top
    ]), hide_index=True)

    # ---- Simulador: cómo cambia la pérdida según los comensales ----
    st.markdown("##### Simulador de merma según comensales")
    st.caption("Como los productos son indivisibles, la pérdida sube y baja en 'dientes de sierra'. "
               "Sirve para sugerir tamaños de servicio que minimizan el desecho.")
    catalogo = repositorio.cargar_catalogo()
    s1, s2 = st.columns([2, 1])
    menu = s1.selectbox("Menú a simular", [r.nombre for r in catalogo.recetas])
    tope = s2.slider("Comensales máximos", 4, 100, 40)
    receta = catalogo.buscar_receta(menu)
    sim = [{"comensales": n, "perdida": calcular_orden(receta, n).perdida_total} for n in range(1, tope + 1)]
    st.line_chart(pd.DataFrame(sim).set_index("comensales"))
    sin_merma = [s["comensales"] for s in sim if s["perdida"] == 0]
    if sin_merma:
        st.success(f"Con {', '.join(map(str, sin_merma))} comensales este menú no genera merma.")
    else:
        st.info("En este rango no hay una cantidad de comensales con merma cero.")


# ---------------------------------------------------------------------------
# Página 4: Consultar insumos (búsqueda secuencial + grafo)
# ---------------------------------------------------------------------------
def catalogo() -> None:
    exigir_rol("administrador")
    st.title("🔎 Consultar insumos")
    cat = repositorio.cargar_catalogo()

    texto = st.text_input("Buscar ingrediente", placeholder="Ej: papa").strip().lower()
    encontrados = busqueda_secuencial_todos(cat.ingredientes, lambda i: texto in i.nombre.lower())
    st.caption(f"{len(encontrados)} de {len(cat.ingredientes)} ingredientes (búsqueda secuencial).")
    st.dataframe(pd.DataFrame([
        {"Ingrediente": i.nombre, "Unidad de compra": i.unidad_compra,
         "Costo envase": formato_pesos(i.costo_envase), "Rinde (personas)": i.personas_por_envase,
         "Costo por porción": formato_pesos(i.costo_por_porcion),
         "Menús que lo usan (grafo)": ", ".join(cat.menus_que_usan(i.nombre)) or "—"}
        for i in encontrados
    ]), hide_index=True)

    st.markdown("##### Recetas cargadas")
    st.dataframe(pd.DataFrame([
        {"Menú": r.nombre, "Base": r.comensales_base,
         "Ingredientes (cantidad receta original)":
             "; ".join(f"{n}: {c}" for n, c in r.cantidades_base.items())}
        for r in cat.recetas
    ]), hide_index=True)
