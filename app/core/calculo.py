"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Profesor  : Dr. Carlos Santibáñez Rodríguez
Fecha     : 26-nov-2026
Archivo   : app/core/calculo.py
Librerías : math (estándar)

Actividad 2 — Motor de cálculo y gestión de mermas.

Para cada ingrediente del menú, con  n = comensales  y  p = personas_por_envase:

    envases             = ceil(n / p)            (productos indivisibles → se redondea hacia arriba)
    porciones_compradas = envases · p
    porciones_sobrantes = envases · p − n        (merma física, en porciones)
    merma_envase        = porciones_sobrantes / p  (merma física, en fracción de envase)
    costo_linea         = envases · costo_envase
    pérdida             = merma_envase · costo_envase

Para la orden completa:

    costo_total     = Σ costo_linea
    costo_por_plato = costo_total / n
    precio_venta    = costo_por_plato · (1 + 0,25)
    ingreso         = precio_venta · n
    pérdida_total   = Σ pérdida

DECISIONES:
  1. Manda el rendimiento ("utilidad") de la tabla de ingredientes, no las
     cantidades de la receta: la receta define QUÉ ingredientes lleva el menú.
  2. Ganancia del 25 % aplicada sobre el costo (markup): precio = costo × 1,25.
  3. Como nada se puede guardar, cada orden abre sus propios envases: la merma
     de una orden NO se reutiliza en la siguiente.

Este módulo NO importa streamlit ni supabase: es lógica pura, independiente de
la interfaz y de la base de datos.
"""
from __future__ import annotations

import math

from core.modelos import Ingrediente, LineaInsumo, Orden, Receta

MARGEN_GANANCIA = 0.25


def validar_comensales(valor) -> int:
    """Acepta solo enteros mayores que cero. Lanza ValueError con un mensaje claro
    si el valor es nulo, no numérico, decimal, negativo o cero."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ValueError("Debe ingresar la cantidad de comensales.")
    if isinstance(valor, bool):                       # True/False no son cantidades
        raise ValueError("La cantidad de comensales debe ser un número entero.")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError("La cantidad de comensales debe ser un número entero.") from None
    if math.isnan(numero) or math.isinf(numero) or numero != int(numero):
        raise ValueError("La cantidad de comensales debe ser un número entero (sin decimales).")
    numero = int(numero)
    if numero <= 0:
        raise ValueError("La cantidad de comensales debe ser mayor que cero.")
    return numero


def calcular_linea(ingrediente: Ingrediente, comensales: int) -> LineaInsumo:
    """Requerimiento, merma y pérdida de UN ingrediente para 'comensales' personas."""
    p = ingrediente.personas_por_envase
    envases = math.ceil(comensales / p)               # pauta: redondeo hacia arriba
    porciones_compradas = envases * p
    porciones_sobrantes = porciones_compradas - comensales
    merma_envase = porciones_sobrantes / p
    costo_linea = envases * ingrediente.costo_envase
    perdida = merma_envase * ingrediente.costo_envase
    return LineaInsumo(ingrediente, comensales, envases, porciones_sobrantes,
                       merma_envase, costo_linea, perdida)


def calcular_orden(receta: Receta, comensales) -> Orden:
    """Aplica calcular_linea a cada ingrediente de la receta y suma los totales."""
    n = validar_comensales(comensales)
    if not receta.ingredientes:
        raise ValueError(f"La receta '{receta.nombre}' no tiene ingredientes cargados.")

    lineas = [calcular_linea(ing, n) for ing in receta.ingredientes]
    costo_total = sum(l.costo_linea for l in lineas)
    perdida_total = sum(l.perdida for l in lineas)
    costo_por_plato = costo_total / n
    precio_venta_plato = costo_por_plato * (1 + MARGEN_GANANCIA)
    ingreso_proyectado = precio_venta_plato * n
    return Orden(receta, n, lineas, costo_total, costo_por_plato,
                 precio_venta_plato, ingreso_proyectado, perdida_total)


def formato_pesos(valor: float) -> str:
    """$12.345 (separador de miles chileno, sin decimales)."""
    return "$" + f"{round(valor):,}".replace(",", ".")
