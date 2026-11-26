-- =====================================================================
-- Evaluación N°3 — Programación Avanzada (ACAPOMIL)
-- Sistema de inventario de alimentos, control y gestión de mermas
-- Autor    : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
-- Profesor : Dr. Carlos Santibáñez Rodríguez
-- Fecha    : 26-nov-2026
-- Archivo  : sql/01_esquema.sql  (ejecutar 1° en Supabase → SQL Editor)
--
-- Actividad 1 — Modelamiento de la base de datos.
--   * Catálogo   : ingredientes, recetas, receta_ingredientes
--   * Operación  : ordenes (cabecera de cada servicio) + orden_detalle (insumos)
--   * Perfiles   : usuarios (rol 'cocina' | 'administrador')
--
-- DECISIÓN: ordenes y orden_detalle guardan una "foto" (snapshot) del nombre,
-- costo y rendimiento del ingrediente al momento del cálculo. Así, si mañana
-- cambia el precio de la cebolla, el historial sigue mostrando lo que realmente
-- se gastó ese día (trazabilidad de gasto público).
-- =====================================================================

-- Para poder re-ejecutar el script desde cero (orden inverso por las FK).
drop function if exists public.registrar_orden(jsonb, jsonb);
drop table if exists public.orden_detalle;
drop table if exists public.ordenes;
drop table if exists public.receta_ingredientes;
drop table if exists public.recetas;
drop table if exists public.ingredientes;
drop table if exists public.usuarios;

-- ---------------------------------------------------------------------
-- 1) Catálogo de ingredientes
--    costo_envase        : precio de 1 unidad de compra indivisible ($)
--    personas_por_envase : "utilidad" de la pauta = comensales que rinde 1 envase
-- ---------------------------------------------------------------------
create table public.ingredientes (
    id                  serial primary key,
    nombre              text    not null unique,
    unidad_compra       text    not null,            -- unidad, paquete, kg, litro, empaque
    costo_envase        integer not null check (costo_envase > 0),
    personas_por_envase integer not null check (personas_por_envase > 0)
);

-- ---------------------------------------------------------------------
-- 2) Recetas (menús) y su relación N:M con ingredientes
--    cantidad_base / unidad_receta guardan la receta tal como la entrega la
--    pauta (base 4 comensales). El motor de cálculo usa el rendimiento del
--    ingrediente; la receta define qué ingredientes lleva cada menú.
-- ---------------------------------------------------------------------
create table public.recetas (
    id               serial primary key,
    nombre           text    not null unique,
    comensales_base  integer not null default 4 check (comensales_base > 0)
);

create table public.receta_ingredientes (
    receta_id      integer not null references public.recetas(id) on delete cascade,
    ingrediente_id integer not null references public.ingredientes(id),
    cantidad_base  numeric not null check (cantidad_base > 0),
    unidad_receta  text    not null,                 -- 'unidades' | 'porciones'
    primary key (receta_id, ingrediente_id)
);

-- ---------------------------------------------------------------------
-- 3) Usuarios y roles (Actividad 1 — Gestión de usuarios y roles)
--    La contraseña NUNCA se guarda en texto plano: solo hash PBKDF2-SHA256 con sal
--    (lo genera scripts/crear_usuarios.py).
-- ---------------------------------------------------------------------
create table public.usuarios (
    id             serial primary key,
    username       text    not null unique,
    nombre         text    not null,
    rol            text    not null check (rol in ('cocina', 'administrador')),
    password_hash  text    not null,
    activo         boolean not null default true
);

-- ---------------------------------------------------------------------
-- 4) Órdenes de servicio (Actividad 1 — Estructura para órdenes y mermas)
-- ---------------------------------------------------------------------
create table public.ordenes (
    id                  bigserial primary key,
    fecha               timestamptz not null default now(),
    receta_id           integer     not null references public.recetas(id),
    receta_nombre       text        not null,                 -- snapshot
    comensales          integer     not null check (comensales > 0),
    usuario             text        not null,                 -- quién la registró
    costo_total         numeric(12,2) not null,               -- Σ envases × costo_envase
    costo_por_plato     numeric(12,2) not null,               -- costo_total / comensales
    precio_venta_plato  numeric(12,2) not null,               -- costo_por_plato × 1,25
    ingreso_proyectado  numeric(12,2) not null,               -- precio_venta × comensales
    perdida_merma       numeric(12,2) not null,               -- Σ pérdidas del detalle
    estado              text        not null default 'pendiente'
                        check (estado in ('pendiente', 'preparada'))
);

create table public.orden_detalle (
    id                   bigserial primary key,
    orden_id             bigint  not null references public.ordenes(id) on delete cascade,
    ingrediente_id       integer not null references public.ingredientes(id),
    ingrediente_nombre   text    not null,                    -- snapshot
    unidad_compra        text    not null,                    -- snapshot
    costo_envase         integer not null,                    -- snapshot
    personas_por_envase  integer not null,                    -- snapshot
    porciones_requeridas integer not null,                    -- = comensales
    envases              integer not null,                    -- ceil(comensales / rendimiento)
    porciones_sobrantes  integer not null,                    -- merma física en porciones
    merma_envase         numeric(8,4)  not null,              -- merma física en fracción de envase
    costo_linea          numeric(12,2) not null,              -- envases × costo_envase
    perdida              numeric(12,2) not null               -- merma_envase × costo_envase
);

create index on public.ordenes (receta_id);
create index on public.orden_detalle (orden_id);

-- ---------------------------------------------------------------------
-- 5) Registro ATÓMICO de una orden (cabecera + detalle en una sola transacción)
--    DECISIÓN: si falla el detalle, PostgreSQL deshace también la cabecera,
--    así nunca queda una orden "huérfana" sin insumos.
-- ---------------------------------------------------------------------
create or replace function public.registrar_orden(p_orden jsonb, p_detalle jsonb)
returns bigint
language plpgsql
security invoker
set search_path = public
as $$
declare
    v_id bigint;
begin
    insert into public.ordenes (receta_id, receta_nombre, comensales, usuario,
                                costo_total, costo_por_plato, precio_venta_plato,
                                ingreso_proyectado, perdida_merma)
    values ((p_orden->>'receta_id')::int,
            p_orden->>'receta_nombre',
            (p_orden->>'comensales')::int,
            p_orden->>'usuario',
            (p_orden->>'costo_total')::numeric,
            (p_orden->>'costo_por_plato')::numeric,
            (p_orden->>'precio_venta_plato')::numeric,
            (p_orden->>'ingreso_proyectado')::numeric,
            (p_orden->>'perdida_merma')::numeric)
    returning id into v_id;

    insert into public.orden_detalle (orden_id, ingrediente_id, ingrediente_nombre,
                unidad_compra, costo_envase, personas_por_envase, porciones_requeridas,
                envases, porciones_sobrantes, merma_envase, costo_linea, perdida)
    select v_id,
           (d->>'ingrediente_id')::int,
           d->>'ingrediente_nombre',
           d->>'unidad_compra',
           (d->>'costo_envase')::int,
           (d->>'personas_por_envase')::int,
           (d->>'porciones_requeridas')::int,
           (d->>'envases')::int,
           (d->>'porciones_sobrantes')::int,
           (d->>'merma_envase')::numeric,
           (d->>'costo_linea')::numeric,
           (d->>'perdida')::numeric
    from jsonb_array_elements(p_detalle) as d;

    return v_id;
end;
$$;

-- ---------------------------------------------------------------------
-- 6) Seguridad a nivel de fila (RLS)
--    La app usa la clave publishable (rol 'anon'). Se habilita RLS en TODAS las
--    tablas y se abre solo lo mínimo:
--      * catálogo y usuarios : solo lectura
--      * ordenes / detalle   : leer e insertar (nunca borrar: trazabilidad)
--      * ordenes.estado      : única columna que se puede actualizar
--    La separación cocina/administrador de las MÉTRICAS se hace en la app
--    (menú por rol + exigir_rol() en cada vista).
-- ---------------------------------------------------------------------
alter table public.ingredientes        enable row level security;
alter table public.recetas             enable row level security;
alter table public.receta_ingredientes enable row level security;
alter table public.usuarios            enable row level security;
alter table public.ordenes             enable row level security;
alter table public.orden_detalle       enable row level security;

create policy "leer ingredientes"  on public.ingredientes        for select to anon, authenticated using (true);
create policy "leer recetas"       on public.recetas             for select to anon, authenticated using (true);
create policy "leer receta_ing"    on public.receta_ingredientes for select to anon, authenticated using (true);
create policy "leer usuarios"      on public.usuarios            for select to anon, authenticated using (true);

create policy "leer ordenes"       on public.ordenes       for select to anon, authenticated using (true);
create policy "insertar ordenes"   on public.ordenes       for insert to anon, authenticated with check (comensales > 0);
create policy "estado ordenes"     on public.ordenes       for update to anon, authenticated using (true) with check (true);
create policy "leer detalle"       on public.orden_detalle for select to anon, authenticated using (true);
create policy "insertar detalle"   on public.orden_detalle for insert to anon, authenticated with check (envases > 0);

-- Privilegios explícitos (no dependemos de los permisos por defecto del proyecto).
grant usage on schema public to anon, authenticated;
grant select on public.ingredientes, public.recetas, public.receta_ingredientes,
               public.usuarios to anon, authenticated;
grant select, insert on public.ordenes, public.orden_detalle to anon, authenticated;
grant usage, select on all sequences in schema public to anon, authenticated;

-- Privilegios por columna: anon solo puede cambiar 'estado' (no costos ni fechas).
revoke update on public.ordenes from anon, authenticated;
grant  update (estado) on public.ordenes to anon, authenticated;
revoke delete on public.ordenes, public.orden_detalle from anon, authenticated;

grant execute on function public.registrar_orden(jsonb, jsonb) to anon, authenticated;
