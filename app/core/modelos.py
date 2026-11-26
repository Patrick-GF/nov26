"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Profesor  : Dr. Carlos Santibáñez Rodríguez
Fecha     : 26-nov-2026
Archivo   : app/core/modelos.py
Librerías : dataclasses (estándar)

Clases del dominio (Indicador IE1: "clases para modelar ingredientes, recetas y órdenes").

    Ingrediente  → un producto del catálogo (costo de 1 envase + cuántas personas rinde)
    Receta       → un menú: nombre + LISTA de ingredientes que lo componen
    LineaInsumo  → resultado del cálculo para 1 ingrediente dentro de una orden
    Orden        → un servicio: receta + comensales + líneas + totales económicos
    Catalogo     → agrupa ingredientes y recetas y arma el GRAFO menú–ingrediente

DECISIÓN: se usan @dataclass porque generan solos __init__, __repr__ y __eq__,
dejando las clases cortas y legibles. Ingrediente es frozen (inmutable) porque
un precio no debe cambiar "por accidente" a mitad de un cálculo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.estructuras import Grafo
from core.ordenamiento import busqueda_secuencial


@dataclass(frozen=True)
class Ingrediente:
    id: int
    nombre: str
    unidad_compra: str          # unidad, paquete, kg, litro, empaque
    costo_envase: int           # $ de 1 envase indivisible
    personas_por_envase: int    # "utilidad" de la pauta

    @property
    def costo_por_porcion(self) -> float:
        """Costo de la porción de 1 comensal: costo_envase / personas_por_envase."""
        return self.costo_envase / self.personas_por_envase


@dataclass
class Receta:
    id: int
    nombre: str
    comensales_base: int
    ingredientes: list[Ingrediente] = field(default_factory=list)   # TDA lista
    # Cantidades de la receta original (base 4). Se guardan para mostrarlas y
    # dejar trazabilidad, pero el cálculo usa el rendimiento del ingrediente.
    cantidades_base: dict[str, str] = field(default_factory=dict)


@dataclass
class LineaInsumo:
    ingrediente: Ingrediente
    porciones_requeridas: int   # = comensales
    envases: int                # unidades completas que se abren (math.ceil)
    porciones_sobrantes: int    # merma física expresada en porciones
    merma_envase: float         # merma física expresada en fracción de envase
    costo_linea: float          # envases × costo_envase
    perdida: float              # merma_envase × costo_envase

    @property
    def cantidad_texto(self) -> str:
        return texto_cantidad(self.envases, self.ingrediente.unidad_compra)


def texto_cantidad(envases: int, unidad: str) -> str:
    """Texto para la cocina, ej. '3 kg', '1 paquete', '2 unidades'."""
    if envases != 1:
        unidad = {"unidad": "unidades", "paquete": "paquetes", "litro": "litros",
                  "empaque": "empaques"}.get(unidad, unidad)
    return f"{envases} {unidad}"


@dataclass
class Orden:
    receta: Receta
    comensales: int
    lineas: list[LineaInsumo]
    costo_total: float
    costo_por_plato: float
    precio_venta_plato: float
    ingreso_proyectado: float
    perdida_total: float

    def a_registro(self, usuario: str) -> tuple[dict, list[dict]]:
        """Convierte la orden en (cabecera, detalle) listos para la función SQL registrar_orden."""
        cabecera = {
            "receta_id": self.receta.id,
            "receta_nombre": self.receta.nombre,
            "comensales": self.comensales,
            "usuario": usuario,
            "costo_total": round(self.costo_total, 2),
            "costo_por_plato": round(self.costo_por_plato, 2),
            "precio_venta_plato": round(self.precio_venta_plato, 2),
            "ingreso_proyectado": round(self.ingreso_proyectado, 2),
            "perdida_merma": round(self.perdida_total, 2),
        }
        detalle = [
            {
                "ingrediente_id": l.ingrediente.id,
                "ingrediente_nombre": l.ingrediente.nombre,
                "unidad_compra": l.ingrediente.unidad_compra,
                "costo_envase": l.ingrediente.costo_envase,
                "personas_por_envase": l.ingrediente.personas_por_envase,
                "porciones_requeridas": l.porciones_requeridas,
                "envases": l.envases,
                "porciones_sobrantes": l.porciones_sobrantes,
                "merma_envase": round(l.merma_envase, 4),
                "costo_linea": round(l.costo_linea, 2),
                "perdida": round(l.perdida, 2),
            }
            for l in self.lineas
        ]
        return cabecera, detalle


class Catalogo:
    """Catálogo en memoria construido con las filas que entrega Supabase.

    Estructuras usadas:
      * listas (ingredientes, recetas) → recorridas con búsqueda secuencial
      * grafo no dirigido menú–ingrediente → "¿qué menús usan este insumo?"
    """

    def __init__(self, filas_ing: list[dict], filas_rec: list[dict], filas_rel: list[dict]):
        self.ingredientes: list[Ingrediente] = [
            Ingrediente(f["id"], f["nombre"], f["unidad_compra"], int(f["costo_envase"]),
                        int(f["personas_por_envase"]))
            for f in filas_ing
        ]
        self.recetas: list[Receta] = [
            Receta(f["id"], f["nombre"], int(f["comensales_base"])) for f in filas_rec
        ]
        self.grafo = Grafo()
        for rel in filas_rel:
            receta = busqueda_secuencial(self.recetas, lambda r: r.id == rel["receta_id"])
            ing = busqueda_secuencial(self.ingredientes, lambda i: i.id == rel["ingrediente_id"])
            if receta is None or ing is None:
                continue  # relación inconsistente: se ignora en vez de botar la app
            receta.ingredientes.append(ing)
            cant = float(rel["cantidad_base"])
            receta.cantidades_base[ing.nombre] = f"{cant:g} {rel['unidad_receta']}"
            # Vértices con prefijo para no confundir un menú con un ingrediente.
            self.grafo.agregar_arista(f"M:{receta.nombre}", f"I:{ing.nombre}")

    def buscar_receta(self, nombre: str) -> Receta | None:
        return busqueda_secuencial(self.recetas, lambda r: r.nombre == nombre)

    def buscar_ingrediente(self, nombre: str) -> Ingrediente | None:
        return busqueda_secuencial(self.ingredientes, lambda i: i.nombre == nombre)

    def menus_que_usan(self, nombre_ingrediente: str) -> list[str]:
        """Vecinos del vértice ingrediente en el grafo = menús que lo contienen."""
        return [v[2:] for v in self.grafo.vecinos(f"I:{nombre_ingrediente}")]
