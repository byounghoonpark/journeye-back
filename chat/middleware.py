from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
import logging
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
User = get_user_model()

class TokenAuthMiddleware(BaseMiddleware):
    """
    WebSocket 연결 시 Authorization 헤더에서 JWT 토큰을 추출하여 인증하는 미들웨어
    """
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        token = None

        # Authorization 헤더에서 JWT 토큰 추출
        if b"authorization" in headers:
            auth_header = headers[b"authorization"].decode()
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token.get("user_id")
                if not user_id:
                    raise Exception("Token payload에 user_id가 없습니다.")
                # 비동기 DB 조회 (sync_to_async 사용)
                user = await sync_to_async(User.objects.get)(id=user_id)
                scope["user"] = user
                logger.info(f"User authenticated: {user}")
            except Exception as e:
                scope["user"] = AnonymousUser()
                logger.error(f"Token authentication failed: {str(e)}")
        else:
            scope["user"] = AnonymousUser()
            logger.warning("No valid token found in WebSocket request")

        return await super().__call__(scope, receive, send)
