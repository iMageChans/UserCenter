from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

class BearerTokenAuthentication(TokenAuthentication):
    """
    自定义令牌认证类，允许不带前缀的令牌
    不需要 'Token' 前缀，直接使用令牌值
    """
    keyword = ''  # 空字符串意味着不需要前缀
    
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '').strip()
        if not auth:
            return None
            
        try:
            token = Token.objects.get(key=auth)
            return (token.user, token)
        except Token.DoesNotExist:
            return None 