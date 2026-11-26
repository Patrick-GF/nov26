"""
Evaluación N°3 — Programación Avanzada (ACAPOMIL)
Autor     : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
Fecha     : 26-nov-2026
Archivo   : scripts/crear_usuarios.py   →  python scripts/crear_usuarios.py
Librerías : secrets, csv (estándar) + core.seguridad

Crea los dos perfiles del sistema ('cocina' y 'admin') con contraseñas aleatorias:
  * credenciales_iniciales.csv → usuario y contraseña en claro (SOLO local, ignorado por git)
  * sql/03_usuarios.sql        → INSERT con los HASH, para pegar en Supabase → SQL Editor
                                 (también ignorado por git)

DECISIÓN: la tabla 'usuarios' no admite INSERT desde la app (RLS), así nadie
puede crearse una cuenta de administrador desde la página.
"""
import csv
import secrets
import string
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "app"))          # para importar core.*

from core.seguridad import hash_password       # noqa: E402

USUARIOS = [
    # username, nombre visible, rol
    ("cocina", "Personal de Cocina", "cocina"),
    ("admin", "Administrador", "administrador"),
]


def clave_aleatoria(largo: int = 10) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(largo))


def main() -> None:
    filas_csv, valores_sql = [], []
    for username, nombre, rol in USUARIOS:
        clave = clave_aleatoria()
        filas_csv.append({"usuario": username, "contraseña": clave, "rol": rol})
        valores_sql.append(f"    ('{username}', '{nombre}', '{rol}', '{hash_password(clave)}')")

    with open(RAIZ / "credenciales_iniciales.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["usuario", "contraseña", "rol"])
        w.writeheader()
        w.writerows(filas_csv)

    sql = ("-- Generado por scripts/crear_usuarios.py — NO subir a GitHub\n"
           "delete from public.usuarios;\n"
           "insert into public.usuarios (username, nombre, rol, password_hash) values\n"
           + ",\n".join(valores_sql) + ";\n")
    (RAIZ / "sql" / "03_usuarios.sql").write_text(sql, encoding="utf-8")

    print("Listo:")
    print("  credenciales_iniciales.csv  (contraseñas en claro, solo local)")
    print("  sql/03_usuarios.sql         (péguelo en Supabase → SQL Editor → Run)")


if __name__ == "__main__":
    main()
