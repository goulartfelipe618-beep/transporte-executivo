"""TrustedHost com bypass em /health para probes Docker/EasyPanel (127.0.0.1)."""

from starlette.middleware.trustedhost import TrustedHostMiddleware


class ProductionHostMiddleware(TrustedHostMiddleware):
    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)
