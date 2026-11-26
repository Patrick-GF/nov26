"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Profesor  : Dr. Carlos Santibáñez Rodríguez
Fecha     : 26-nov-2026
Archivo   : app/core/estructuras.py
Librerías : collections.deque, heapq, itertools (estándar)

Tipos de Datos Abstractos (TDA) — Indicador IE1 / contenidos 4.1 a 4.4.

  TDA            Regla de acceso          Uso en el sistema
  -------------  -----------------------  -----------------------------------------
  Pila           LIFO (último en entrar)  Cocina: "mis últimas órdenes" de la sesión
  Cola           FIFO (primero en entrar) Cocina: cola de preparación de pendientes
  ColaPrioridad  sale la mayor prioridad  Admin: ranking de menús por pérdida
  ArbolBinario   izq < raíz ≤ der         Admin: órdenes ordenadas por pérdida
  Grafo          lista de adyacencia      Catálogo: relación menú–ingrediente

DECISIÓN: cada TDA se implementa como clase propia (no se usa la lista de Python
"a la mala") para que la regla de acceso quede explícita y se pueda defender.
"""
from __future__ import annotations

import heapq
import itertools
from collections import deque
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# PILA (LIFO)
# ---------------------------------------------------------------------------
class Pila:
    """Pila sobre una lista: el tope es el final de la lista (push/pop en O(1))."""

    def __init__(self) -> None:
        self._items: list[Any] = []

    def apilar(self, item: Any) -> None:
        self._items.append(item)

    def desapilar(self) -> Any:
        if self.esta_vacia():
            raise IndexError("La pila está vacía")
        return self._items.pop()

    def tope(self) -> Any:
        if self.esta_vacia():
            raise IndexError("La pila está vacía")
        return self._items[-1]

    def esta_vacia(self) -> bool:
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        """Recorre desde el tope hacia el fondo (orden LIFO)."""
        return reversed(self._items)


# ---------------------------------------------------------------------------
# COLA (FIFO)
# ---------------------------------------------------------------------------
class Cola:
    """Cola sobre collections.deque.

    DECISIÓN: deque y no list, porque list.pop(0) es O(n) (corre todos los
    elementos) y deque.popleft() es O(1).
    """

    def __init__(self) -> None:
        self._items: deque[Any] = deque()

    def encolar(self, item: Any) -> None:
        self._items.append(item)

    def desencolar(self) -> Any:
        if self.esta_vacia():
            raise IndexError("La cola está vacía")
        return self._items.popleft()

    def frente(self) -> Any:
        if self.esta_vacia():
            raise IndexError("La cola está vacía")
        return self._items[0]

    def esta_vacia(self) -> bool:
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)


# ---------------------------------------------------------------------------
# COLA CON PRIORIDAD (max-heap)
# ---------------------------------------------------------------------------
class ColaPrioridad:
    """Cola con prioridad: siempre sale el elemento de MAYOR prioridad.

    heapq de Python es un min-heap, por eso se guarda la prioridad con signo
    negativo. El contador desempata elementos con igual prioridad (sale primero
    el que llegó antes) y evita comparar objetos que no son comparables.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Any]] = []
        self._contador = itertools.count()

    def insertar(self, item: Any, prioridad: float) -> None:
        heapq.heappush(self._heap, (-prioridad, next(self._contador), item))

    def extraer_max(self) -> tuple[Any, float]:
        if self.esta_vacia():
            raise IndexError("La cola con prioridad está vacía")
        prioridad_neg, _, item = heapq.heappop(self._heap)
        return item, -prioridad_neg

    def esta_vacia(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


# ---------------------------------------------------------------------------
# ÁRBOL BINARIO DE BÚSQUEDA
# ---------------------------------------------------------------------------
class NodoArbol:
    def __init__(self, clave: float, valor: Any) -> None:
        self.clave = clave
        self.valor = valor
        self.izq: NodoArbol | None = None
        self.der: NodoArbol | None = None


class ArbolBinarioBusqueda:
    """ABB: claves menores a la izquierda, mayores o IGUALES a la derecha.

    DECISIÓN: los duplicados van a la derecha porque dos órdenes pueden tener
    la misma pérdida y ninguna se debe perder. Inserción y recorridos son
    iterativos para no chocar con el límite de recursión de Python.
    """

    def __init__(self) -> None:
        self.raiz: NodoArbol | None = None
        self._n = 0

    def insertar(self, clave: float, valor: Any) -> None:
        nuevo = NodoArbol(clave, valor)
        self._n += 1
        if self.raiz is None:
            self.raiz = nuevo
            return
        actual = self.raiz
        while True:
            if clave < actual.clave:
                if actual.izq is None:
                    actual.izq = nuevo
                    return
                actual = actual.izq
            else:
                if actual.der is None:
                    actual.der = nuevo
                    return
                actual = actual.der

    def inorden(self, descendente: bool = False) -> list[tuple[float, Any]]:
        """Recorrido en orden con una Pila explícita.

        Ascendente  : izquierda → raíz → derecha
        Descendente : derecha   → raíz → izquierda (de mayor a menor)
        """
        resultado: list[tuple[float, Any]] = []
        pila = Pila()
        actual = self.raiz
        while actual is not None or not pila.esta_vacia():
            while actual is not None:
                pila.apilar(actual)
                actual = actual.der if descendente else actual.izq
            actual = pila.desapilar()
            resultado.append((actual.clave, actual.valor))
            actual = actual.izq if descendente else actual.der
        return resultado

    def altura(self) -> int:
        """Altura por niveles (BFS con la Cola propia)."""
        if self.raiz is None:
            return 0
        cola = Cola()
        cola.encolar((self.raiz, 1))
        maximo = 0
        while not cola.esta_vacia():
            nodo, nivel = cola.desencolar()
            maximo = max(maximo, nivel)
            for hijo in (nodo.izq, nodo.der):
                if hijo is not None:
                    cola.encolar((hijo, nivel + 1))
        return maximo

    def __len__(self) -> int:
        return self._n


# ---------------------------------------------------------------------------
# GRAFO (no dirigido, lista de adyacencia)
# ---------------------------------------------------------------------------
class Grafo:
    """Grafo no dirigido con diccionario {vértice: [vecinos]}.

    En el sistema es BIPARTITO: los vértices 'M:...' son menús y los 'I:...'
    son ingredientes; una arista significa "el menú lleva ese ingrediente".
    """

    def __init__(self) -> None:
        self._ady: dict[str, list[str]] = {}

    def agregar_vertice(self, v: str) -> None:
        self._ady.setdefault(v, [])

    def agregar_arista(self, a: str, b: str) -> None:
        self.agregar_vertice(a)
        self.agregar_vertice(b)
        if b not in self._ady[a]:
            self._ady[a].append(b)
        if a not in self._ady[b]:
            self._ady[b].append(a)

    def vecinos(self, v: str) -> list[str]:
        return list(self._ady.get(v, []))

    def grado(self, v: str) -> int:
        return len(self._ady.get(v, []))

    @property
    def vertices(self) -> list[str]:
        return list(self._ady.keys())

    def recorrido_anchura(self, inicio: str) -> list[str]:
        """BFS con la Cola propia: todos los vértices alcanzables desde 'inicio'."""
        if inicio not in self._ady:
            return []
        visitados = [inicio]
        cola = Cola()
        cola.encolar(inicio)
        while not cola.esta_vacia():
            v = cola.desencolar()
            for w in self._ady[v]:
                if w not in visitados:
                    visitados.append(w)
                    cola.encolar(w)
        return visitados
