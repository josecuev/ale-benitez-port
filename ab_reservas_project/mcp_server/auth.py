"""
Autenticación del servicio MCP — OAuth 2.1.

Reparto de roles:

  Django (django-oauth-toolkit)  = authorization server
      /o/authorize/, /o/token/, /o/register/ (registro dinámico),
      /o/.well-known/oauth-authorization-server
  Este servicio                  = resource server
      valida el access token y publica su metadata RFC 9728

Como el MCP comparte base con Django, el token se valida leyendo la tabla de
DOT directamente: sin round-trip HTTP a /o/introspect/ y con revocación
instantánea desde el admin.

Regla de arranque (fail-closed): con transporte HTTP fuera de modo debug, sin
autenticación el servicio no levanta.
"""
import os

from fastmcp.server.auth import AccessToken, RemoteAuthProvider, TokenVerifier

from .bootstrap import con_db

SCOPE = "fractalia:operar"


class ConfiguracionInsegura(RuntimeError):
    pass


class VerificadorDOT(TokenVerifier):
    """Valida el bearer contra la tabla de access tokens de django-oauth-toolkit."""

    @con_db
    def _buscar(self, token: str):
        import hashlib

        from oauth2_provider.models import AccessToken as DotToken

        # Se busca por token_checksum y no por token: DOT mantiene siempre ese
        # SHA-256, así que la consulta sigue funcionando con almacenamiento
        # hasheado (COMPLIANT_BCP_RFC9700_TOKEN_STORAGE=True), donde la columna
        # `token` queda vacía.
        checksum = hashlib.sha256(token.encode("utf-8")).hexdigest()
        obj = (DotToken.objects
               .select_related("user", "application")
               .filter(token_checksum=checksum)
               .first())
        if obj is None or not obj.is_valid([SCOPE]):
            return None
        # Un token sin usuario es de client_credentials: no aplica acá, porque
        # todas las operaciones se atribuyen a una persona.
        if obj.user is None or not obj.user.is_active:
            return None
        return {
            "usuario": obj.user.get_username(),
            "scopes": obj.scope.split() if obj.scope else [SCOPE],
            "expira": int(obj.expires.timestamp()) if obj.expires else None,
            "app": obj.application.name if obj.application else "",
        }

    async def verify_token(self, token: str) -> AccessToken | None:
        from asgiref.sync import sync_to_async

        datos = await sync_to_async(self._buscar, thread_sensitive=True)(token)
        if datos is None:
            return None
        return AccessToken(
            token=token,
            client_id=datos["app"] or datos["usuario"],
            subject=datos["usuario"],
            scopes=datos["scopes"],
            expires_at=datos["expira"],
            claims={"usuario": datos["usuario"]},
        )


def construir_auth(transporte: str, debug: bool):
    """
    AuthProvider para FastMCP, o None cuando corre en stdio.

    stdio no se autentica: el cliente es dueño del proceso y no hay red de por
    medio. HTTP siempre exige OAuth, salvo modo debug explícito.
    """
    if transporte != "http":
        return None

    if os.environ.get("MCP_SIN_AUTH") == "1":
        if not debug:
            raise ConfiguracionInsegura(
                "MCP_SIN_AUTH=1 solo se admite con DEBUG=1. "
                "En producción el servicio no arranca sin autenticación."
            )
        print("[mcp] AVISO: HTTP sin autenticación (DEBUG=1 + MCP_SIN_AUTH=1). "
              "Nunca levantes así con datos reales.", flush=True)
        return None

    emisor = os.environ.get("OAUTH_ISSUER", "https://admin.alejandrobenitez.com")
    propio = os.environ.get("MCP_PUBLIC_URL", "https://mcp.alejandrobenitez.com")

    return RemoteAuthProvider(
        token_verifier=VerificadorDOT(),
        authorization_servers=[f"{emisor}/o"],
        base_url=propio,
        scopes_supported=[SCOPE],
        resource_name="Fractalia — gestión de reservas",
    )
