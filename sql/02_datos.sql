-- =====================================================================
-- Evaluación N°3 — Programación Avanzada (ACAPOMIL)
-- Autor    : Tte. Patrick Gatica F. — I CRIM Sistema de Armas
-- Fecha    : 26-nov-2026
-- Archivo  : sql/02_datos.sql  (ejecutar 2° en Supabase → SQL Editor)
--
-- Actividad 1 — Población inicial: 10 ingredientes y 10 recetas de la pauta.
-- Los usuarios se cargan aparte con el SQL que imprime scripts/crear_usuarios.py
-- (así ninguna contraseña ni hash queda escrito en el repositorio).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Ingredientes: costo de 1 envase indivisible y cuántas personas rinde.
-- DECISIÓN: "Tuto de pollo" se escribe tal cual aparece en la pauta.
-- ---------------------------------------------------------------------
insert into public.ingredientes (nombre, unidad_compra, costo_envase, personas_por_envase) values
    ('Cebolla',       'unidad',  500,  4),
    ('Arroz',         'paquete', 1500, 10),
    ('Tuto de pollo', 'unidad',  1200, 1),
    ('Carne molida',  'paquete', 1500, 4),
    ('Papa',          'kg',      1000, 4),
    ('Tomate',        'kg',      1500, 4),
    ('Fideos',        'paquete', 1200, 4),
    ('Lechuga',       'unidad',  1000, 10),
    ('Huevo',         'empaque', 4500, 12),
    ('Aceite',        'litro',   1000, 10);

-- ---------------------------------------------------------------------
-- Recetas (todas con base 4 comensales)
-- ---------------------------------------------------------------------
insert into public.recetas (nombre, comensales_base) values
    ('Arroz con Pollo y Ensalada',          4),
    ('Carne Molida con Papas',              4),
    ('Tallarines con Salsa de Tomate',      4),
    ('Tortilla de Papas y Cebolla',         4),
    ('Pollo Salteado con Verduras',         4),
    ('Charquicán Simple',                   4),
    ('Fideos con Huevo y Tomate',           4),
    ('Carne Molida con Arroz y Ensalada',   4),
    ('Papas Cocidas con Huevo y Lechuga',   4),
    ('Arroz Graneado con Huevo y Cebolla',  4);

-- ---------------------------------------------------------------------
-- Relación receta → ingredientes, buscando los id por nombre (subconsulta)
-- para no depender del número que asigne el serial.
-- ---------------------------------------------------------------------
insert into public.receta_ingredientes (receta_id, ingrediente_id, cantidad_base, unidad_receta)
select r.id, i.id, v.cantidad, v.unidad
from (values
    ('Arroz con Pollo y Ensalada',         'Tuto de pollo', 4, 'unidades'),
    ('Arroz con Pollo y Ensalada',         'Arroz',         4, 'porciones'),
    ('Arroz con Pollo y Ensalada',         'Lechuga',       1, 'unidades'),
    ('Arroz con Pollo y Ensalada',         'Aceite',        4, 'porciones'),

    ('Carne Molida con Papas',             'Carne molida',  4, 'porciones'),
    ('Carne Molida con Papas',             'Papa',          6, 'unidades'),
    ('Carne Molida con Papas',             'Cebolla',       1, 'unidades'),
    ('Carne Molida con Papas',             'Aceite',        4, 'porciones'),

    ('Tallarines con Salsa de Tomate',     'Fideos',        4, 'porciones'),
    ('Tallarines con Salsa de Tomate',     'Tomate',        4, 'unidades'),
    ('Tallarines con Salsa de Tomate',     'Cebolla',       1, 'unidades'),
    ('Tallarines con Salsa de Tomate',     'Aceite',        4, 'porciones'),

    ('Tortilla de Papas y Cebolla',        'Papa',          6, 'unidades'),
    ('Tortilla de Papas y Cebolla',        'Cebolla',       1, 'unidades'),
    ('Tortilla de Papas y Cebolla',        'Huevo',         6, 'unidades'),
    ('Tortilla de Papas y Cebolla',        'Aceite',        4, 'porciones'),

    ('Pollo Salteado con Verduras',        'Tuto de pollo', 4, 'unidades'),
    ('Pollo Salteado con Verduras',        'Tomate',        3, 'unidades'),
    ('Pollo Salteado con Verduras',        'Cebolla',       1, 'unidades'),
    ('Pollo Salteado con Verduras',        'Aceite',        4, 'porciones'),

    ('Charquicán Simple',                  'Papa',          6, 'unidades'),
    ('Charquicán Simple',                  'Lechuga',       1, 'unidades'),
    ('Charquicán Simple',                  'Cebolla',       1, 'unidades'),
    ('Charquicán Simple',                  'Aceite',        4, 'porciones'),

    ('Fideos con Huevo y Tomate',          'Fideos',        4, 'porciones'),
    ('Fideos con Huevo y Tomate',          'Huevo',         4, 'unidades'),
    ('Fideos con Huevo y Tomate',          'Tomate',        3, 'unidades'),
    ('Fideos con Huevo y Tomate',          'Aceite',        4, 'porciones'),

    ('Carne Molida con Arroz y Ensalada',  'Carne molida',  4, 'porciones'),
    ('Carne Molida con Arroz y Ensalada',  'Arroz',         4, 'porciones'),
    ('Carne Molida con Arroz y Ensalada',  'Lechuga',       1, 'unidades'),
    ('Carne Molida con Arroz y Ensalada',  'Tomate',        2, 'unidades'),

    ('Papas Cocidas con Huevo y Lechuga',  'Papa',          6, 'unidades'),
    ('Papas Cocidas con Huevo y Lechuga',  'Huevo',         4, 'unidades'),
    ('Papas Cocidas con Huevo y Lechuga',  'Lechuga',       1, 'unidades'),
    ('Papas Cocidas con Huevo y Lechuga',  'Aceite',        4, 'porciones'),

    ('Arroz Graneado con Huevo y Cebolla', 'Arroz',         4, 'porciones'),
    ('Arroz Graneado con Huevo y Cebolla', 'Huevo',         4, 'unidades'),
    ('Arroz Graneado con Huevo y Cebolla', 'Cebolla',       1, 'unidades'),
    ('Arroz Graneado con Huevo y Cebolla', 'Aceite',        4, 'porciones')
) as v(receta, ingrediente, cantidad, unidad)
join public.recetas      r on r.nombre = v.receta
join public.ingredientes i on i.nombre = v.ingrediente;

-- Verificación rápida: debe dar 10 | 10 | 40
select (select count(*) from public.ingredientes)        as ingredientes,
       (select count(*) from public.recetas)             as recetas,
       (select count(*) from public.receta_ingredientes) as relaciones;
