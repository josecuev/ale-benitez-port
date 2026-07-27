-- Rol de solo lectura para el tool consulta_sql del servicio MCP.
--
-- La idea: que el límite lo imponga Postgres y no una lista negra de texto.
-- Este rol solo puede hacer SELECT sobre las tablas de negocio; auth_user,
-- django_session y el resto simplemente no existen para él. Si algún día se
-- burla un filtro del código, acá no se lee nada de más.
--
-- Uso:
--   psql -U postgres -d ab_reservas -v clave="'la-clave-generada'" \
--        -f rol_lectura_mcp.sql
--
-- La clave va después en MCP_SQL_PASSWORD, en el entorno del servicio MCP.

\set ON_ERROR_STOP on

-- Crear o actualizar el rol sin fallar si ya existe.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_lectura') THEN
        CREATE ROLE mcp_lectura LOGIN;
    END IF;
END
$$;

ALTER ROLE mcp_lectura LOGIN PASSWORD :clave;

-- Sin privilegios heredados de nada: se parte de cero.
ALTER ROLE mcp_lectura NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

REVOKE ALL ON DATABASE ab_reservas FROM mcp_lectura;
REVOKE ALL ON SCHEMA public FROM mcp_lectura;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM mcp_lectura;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM mcp_lectura;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM mcp_lectura;

-- Lo mínimo para poder consultar.
GRANT CONNECT ON DATABASE ab_reservas TO mcp_lectura;
GRANT USAGE ON SCHEMA public TO mcp_lectura;

-- Solo lectura, y solo sobre las tablas de negocio.
GRANT SELECT ON
    app_fractalia_pendingbooking,
    app_fractalia_booking,
    app_fractalia_product,
    app_fractalia_fractaboxpackage,
    app_fractalia_resource,
    app_fractalia_weeklyavailability,
    app_analytics_pageview,
    app_analytics_pageviewmonthly,
    app_links_link,
    app_portfolio_photo,
    -- Historial de acciones del admin: guarda user_id, no credenciales, y
    -- esquema() lo lista, así que se concede para que no queden inconsistencias.
    django_admin_log
TO mcp_lectura;

-- Que las tablas que se creen a futuro NO queden accesibles por defecto:
-- si mañana aparece una tabla con datos sensibles, hay que concederla a mano.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM mcp_lectura;

-- Verificación: qué puede leer realmente el rol.
SELECT table_name AS "tablas visibles para mcp_lectura"
FROM information_schema.table_privileges
WHERE grantee = 'mcp_lectura' AND privilege_type = 'SELECT'
ORDER BY table_name;
