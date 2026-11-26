"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Profesor  : Dr. Carlos Santibáñez Rodríguez
Fecha     : 26-nov-2026
Archivo   : app/core/ordenamiento.py
Librerías : heapq, json, os, tempfile (estándar)

Algoritmos de búsqueda y ordenamiento — Indicadores IE4 e IE5 / contenidos 5.1 a 5.3.

  Algoritmo                 Tipo      Complejidad   Uso en el sistema
  ------------------------  --------  ------------  ----------------------------------
  busqueda_secuencial       búsqueda  O(n)          login, catálogo, consultar insumos
  merge_sort                interno   O(n log n)    ordenar la tabla del historial
  ordenamiento_externo      externo   O(n log n)    exportar historial a CSV por bloques

DECISIÓN — ¿por qué Merge Sort?
  * Es ESTABLE: si dos órdenes tienen la misma pérdida, mantienen su orden por
    fecha (importante para la trazabilidad).
  * Su costo es O(n log n) siempre (Quick Sort cae a O(n²) en el peor caso).
  * Es la misma idea que usa el ordenamiento externo para mezclar bloques.

DECISIÓN — ¿por qué un ordenamiento externo?
  Simula el caso en que el historial no cabe en memoria RAM: se divide en
  bloques, cada bloque se ordena en memoria y se guarda en un archivo temporal
  ("run"), y luego los archivos se MEZCLAN leyendo una línea a la vez de cada uno.
"""
from __future__ import annotations

import heapq
import json
import os
import tempfile
from typing import Any, Callable

Clave = Callable[[Any], Any]


# ---------------------------------------------------------------------------
# BÚSQUEDA SECUENCIAL
# ---------------------------------------------------------------------------
def busqueda_secuencial(lista: list, condicion: Callable[[Any], bool]) -> Any | None:
    """Recorre la lista de inicio a fin y devuelve el PRIMER elemento que cumple
    la condición; si ninguno la cumple devuelve None. Peor caso: n comparaciones."""
    for elemento in lista:
        if condicion(elemento):
            return elemento
    return None


def busqueda_secuencial_todos(lista: list, condicion: Callable[[Any], bool]) -> list:
    """Igual que la anterior, pero recorre TODA la lista y junta todas las coincidencias."""
    encontrados = []
    for elemento in lista:
        if condicion(elemento):
            encontrados.append(elemento)
    return encontrados


# ---------------------------------------------------------------------------
# ORDENAMIENTO INTERNO: MERGE SORT
# ---------------------------------------------------------------------------
def _va_antes(a: Any, b: Any, clave: Clave, descendente: bool) -> bool:
    """True si 'a' debe quedar antes que 'b'. Con '<=' (y '>=') se preserva la
    estabilidad: ante empate gana el que venía primero (el de la izquierda)."""
    ka, kb = clave(a), clave(b)
    return ka >= kb if descendente else ka <= kb


def _mezclar(izq: list, der: list, clave: Clave, descendente: bool) -> list:
    """Mezcla dos listas YA ordenadas en una sola lista ordenada."""
    resultado = []
    i = j = 0
    while i < len(izq) and j < len(der):
        if _va_antes(izq[i], der[j], clave, descendente):
            resultado.append(izq[i])
            i += 1
        else:
            resultado.append(der[j])
            j += 1
    resultado.extend(izq[i:])   # lo que sobra ya está ordenado
    resultado.extend(der[j:])
    return resultado


def merge_sort(lista: list, clave: Clave = lambda x: x, descendente: bool = False) -> list:
    """Divide y vencerás: parte la lista por la mitad, ordena cada mitad
    (recursivamente) y las mezcla. Devuelve una lista NUEVA (no modifica la original)."""
    if len(lista) <= 1:
        return list(lista)
    medio = len(lista) // 2
    izq = merge_sort(lista[:medio], clave, descendente)
    der = merge_sort(lista[medio:], clave, descendente)
    return _mezclar(izq, der, clave, descendente)


# ---------------------------------------------------------------------------
# ORDENAMIENTO EXTERNO: MERGE SORT EXTERNO (k-vías)
# ---------------------------------------------------------------------------
class _Invertido:
    """Envoltorio que invierte la comparación '<' para mezclar en orden descendente
    con heapq (que siempre saca el menor). Sirve para números y textos."""

    __slots__ = ("v",)

    def __init__(self, v: Any) -> None:
        self.v = v

    def __lt__(self, otro: "_Invertido") -> bool:
        return otro.v < self.v

    def __eq__(self, otro: object) -> bool:   # necesario para desempatar por n° de run
        return isinstance(otro, _Invertido) and self.v == otro.v


def ordenamiento_externo(registros: list[dict], clave: Clave, tam_bloque: int = 5,
                         descendente: bool = False) -> tuple[list[dict], int]:
    """Ordena 'registros' usando archivos temporales. Devuelve (ordenados, n_bloques).

    Fase 1 — Generar runs : se toman 'tam_bloque' registros, se ordenan en memoria
                            con merge_sort y se escriben a un archivo (1 JSON por línea).
    Fase 2 — Mezcla k-vías: se abre cada archivo, se lee SOLO su primera línea y se
                            pone en un heap; se saca la menor (o mayor), se escribe al
                            resultado y se lee la siguiente línea de ESE archivo.
                            En memoria hay a lo más k registros a la vez (k = n° de runs).
    """
    if tam_bloque < 1:
        raise ValueError("tam_bloque debe ser >= 1")

    carpeta = tempfile.mkdtemp(prefix="runs_")
    rutas: list[str] = []
    try:
        # ---------------- Fase 1 ----------------
        for inicio in range(0, len(registros), tam_bloque):
            bloque = merge_sort(registros[inicio:inicio + tam_bloque], clave, descendente)
            ruta = os.path.join(carpeta, f"run_{len(rutas):03d}.jsonl")
            with open(ruta, "w", encoding="utf-8") as f:
                for reg in bloque:
                    f.write(json.dumps(reg, ensure_ascii=False, default=str) + "\n")
            rutas.append(ruta)

        # ---------------- Fase 2 ----------------
        archivos = [open(r, encoding="utf-8") for r in rutas]
        try:
            heap: list[tuple[Any, int, dict]] = []
            for idx, f in enumerate(archivos):
                linea = f.readline()
                if linea:
                    reg = json.loads(linea)
                    k = clave(reg)
                    # idx desempata: ante igual clave sale el run anterior (estabilidad)
                    heapq.heappush(heap, (_Invertido(k) if descendente else k, idx, reg))
            ordenados: list[dict] = []
            while heap:
                _, idx, reg = heapq.heappop(heap)
                ordenados.append(reg)
                linea = archivos[idx].readline()
                if linea:
                    sig = json.loads(linea)
                    k = clave(sig)
                    heapq.heappush(heap, (_Invertido(k) if descendente else k, idx, sig))
        finally:
            for f in archivos:
                f.close()
        return ordenados, len(rutas)
    finally:
        # Limpieza: los runs son temporales, no deben quedar en disco.
        for r in rutas:
            if os.path.exists(r):
                os.remove(r)
        os.rmdir(carpeta)
