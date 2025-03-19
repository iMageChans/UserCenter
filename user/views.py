import json
import time

from django.contrib.auth import get_user_model, authenticate
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, datetime
import requests
import logging
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny, IsAdminUser
import jwt
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.translation import gettext as _
from .utils import api_response
from django.contrib.auth.models import UserManager
from django.utils import translation
import pytz

from .models import OAuthProvider, UserOAuth
from .serializers import (
    UserSerializer, OAuthProviderSerializer,
    SocialLoginSerializer, UserRegistrationSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    """
    用户视图集
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        限制普通用户只能查看自己的信息
        """
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        获取当前用户信息
        """
        user = request.user
        
        # 检查付费状态是否过期
        if user.is_premium and user.premium_expiry and user.premium_expiry < timezone.now():
            # 付费已过期，更新用户状态
            user.is_premium = False
            user.premium_expiry = None
            user.save(update_fields=['is_premium', 'premium_expiry'])
            logger.info(f"用户 {user.username} (ID: {user.id}) 的付费状态已过期并更新")
        
        serializer = self.get_serializer(user)
        return Response(api_response(
            code=200,
            message=_('获取成功'),
            data=serializer.data
        ))
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        修改密码
        """
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(api_response(
                code=400,
                message='旧密码和新密码不能为空',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 验证旧密码
        if not request.user.check_password(old_password):
            return Response(api_response(
                code=400,
                message='原密码不正确',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 设置新密码
        request.user.set_password(new_password)
        request.user.save()
        
        return Response(api_response(
            code=200,
            message='密码修改成功',
            data=None
        ))
    
    @action(detail=False, methods=['get'])
    def oauth_accounts(self, request):
        """
        获取用户关联的第三方账号
        """
        oauth_accounts = UserOAuth.objects.filter(user=request.user).select_related('provider')
        
        # 自定义序列化
        data = []
        for oauth in oauth_accounts:
            data.append({
                'id': oauth.id,
                'provider': {
                    'id': oauth.provider.id,
                    'name': oauth.provider.name,
                    'is_active': oauth.provider.is_active
                },
                'provider_user_id': oauth.provider_user_id,
                'created_at': oauth.created_at.timestamp() * 1000
            })
        
        return Response(api_response(
            code=200,
            message='获取成功',
            data=data
        ))

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def update_premium_status(self, request, pk=None):
        """
        更新用户的付费状态（仅限管理员）
        
        参数:
        - is_premium: 布尔值，表示用户是否为付费用户
        - duration_type: 字符串，付费时长类型，可选值：'week'(周)、'month'(月)、'quarter'(季度)、'year'(年)
        """
        try:
            user = self.get_object()
            # 获取请求参数
            is_premium = request.data.get('is_premium')
            expires_at = request.data.get('expires_at')  # 默认为月
            
            # 验证参数
            if is_premium is None:
                return Response(api_response(
                    code=400,
                    message=_('缺少必要参数: is_premium'),
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 更新付费状态
            user.is_premium = is_premium
            user.premium_expiry = expires_at
            
            # 保存用户
            user.save()
            
            # 返回更新后的用户信息
            serializer = self.get_serializer(user)
            return Response(api_response(
                code=200,
                message=_('用户付费状态更新成功'),
                data=serializer.data
            ))
        
        except Exception as e:
            logger.error(f"更新用户付费状态失败: {str(e)}", exc_info=True)
            return Response(api_response(
                code=500,
                message=_('更新用户付费状态失败'),
                data={'detail': str(e)}
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OAuthProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    OAuth提供商视图集
    """
    queryset = OAuthProvider.objects.filter(is_active=True)
    serializer_class = OAuthProviderSerializer
    permission_classes = [permissions.AllowAny]

class SocialLoginView(APIView):
    """
    社交登录视图
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider_name = serializer.validated_data['provider']
        code = serializer.validated_data['code']
        redirect_uri = serializer.validated_data.get('redirect_uri')
        app_id = serializer.validated_data.get('app_id', 'default')  # 添加 app_id 参数
        
        try:
            # 根据 provider_name 和 app_id 查找提供商配置
            provider = OAuthProvider.objects.get(name=provider_name, app_id=app_id, is_active=True)
        except OAuthProvider.DoesNotExist:
            # 如果找不到特定应用的配置，尝试查找默认配置
            try:
                provider = OAuthProvider.objects.get(name=provider_name, app_id='default', is_active=True)
            except OAuthProvider.DoesNotExist:
                return Response(api_response(
                    code=400,
                    message=f'不支持的登录方式: {provider_name} (app_id: {app_id})',
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
        
        # 根据不同的提供商处理OAuth流程
        handler_method = getattr(self, f'handle_{provider_name}_login', None)
        if not handler_method:
            return Response(api_response(
                code=501,
                message=f'未实现的登录方式: {provider_name}',
                data=None
            ), status=status.HTTP_501_NOT_IMPLEMENTED)
        
        try:
            return handler_method(provider, code, redirect_uri)
        except Exception as e:
            logger.exception(f"社交登录失败: {provider_name}")
            return Response(api_response(
                code=400,
                message='登录失败',
                data={'detail': str(e)}
            ), status=status.HTTP_400_BAD_REQUEST)
    
    def handle_wechat_login(self, provider, code, redirect_uri=None):
        """处理微信登录"""
        # 获取访问令牌
        token_url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
        
        # 使用数据库中的配置
        client_id = provider.client_id
        client_secret = provider.client_secret
        
        token_params = {
            'appid': client_id,
            'secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        
        if 'errcode' in token_data:
            return Response(api_response(
                code=400,
                message=f'微信授权失败: {token_data["errmsg"]}',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 获取用户信息
        user_url = 'https://api.weixin.qq.com/sns/userinfo'
        user_params = {
            'access_token': token_data['access_token'],
            'openid': token_data['openid'],
            'lang': 'zh_CN'
        }
        
        user_response = requests.get(user_url, params=user_params)
        user_data = user_response.json()
        
        if 'errcode' in user_data:
            return Response(api_response(
                code=400,
                message=f'获取微信用户信息失败: {user_data["errmsg"]}',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 查找或创建用户
        return self._get_or_create_user(
            provider=provider,
            provider_user_id=user_data['openid'],
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=token_data.get('expires_in', 7200),
            user_data=user_data,
            username=f"wx_{user_data['openid']}",
            email='',  # 微信不提供邮箱
            nickname=user_data.get('nickname', 'username'),
            avatar=user_data.get('headimgurl', '')
        )
    
    def handle_apple_login(self, provider, code, redirect_uri=None):
        """处理苹果登录"""
        request = self.request  # 从类实例获取 request
        # 获取访问令牌
        token_url = 'https://appleid.apple.com/auth/token'
        
        # 使用数据库中的配置
        client_id = provider.client_id
        client_secret = self._generate_apple_client_secret(provider)
        
        # 获取重定向URI
        redirect_uri = redirect_uri or provider.redirect_uri
        
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_result = token_response.json()
        
        if 'error' in token_result:
            return Response(api_response(
                code=400,
                message=f'苹果授权失败: {token_result.get("error_description", token_result["error"])}',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 解析ID令牌以获取用户信息
        id_token = token_result.get('id_token')
        if not id_token:
            return Response(api_response(
                code=400,
                message='苹果登录失败: 未获取到ID令牌',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 解码JWT但不验证签名
            jwt_payload = jwt.decode(id_token, options={"verify_signature": False})
            
            # 获取用户标识符
            user_id = jwt_payload.get('sub')
            if not user_id:
                return Response(api_response(
                    code=400,
                    message='苹果登录失败: 未获取到用户标识符',
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 获取邮箱和姓名
            email = jwt_payload.get('email', '')
            
            # 用户名可能在请求体的user字段中
            user_data = {}
            if 'user' in request.data:
                try:
                    user_info = json.loads(request.data['user'])
                    name = user_info.get('name', {})
                    first_name = name.get('firstName', '')
                    last_name = name.get('lastName', '')
                    nickname = f"{first_name} {last_name}".strip()
                    user_data = {
                        'name': nickname,
                        'email': email
                    }
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # 查找或创建用户
            return self._get_or_create_user(
                provider=provider,
                provider_user_id=user_id,
                access_token=token_result.get('access_token', ''),
                refresh_token=token_result.get('refresh_token', ''),
                expires_in=token_result.get('expires_in'),
                user_data=user_data,
                username=f"apple_{user_id}",
                email=email,
                nickname=user_data.get('name', 'username'),
                avatar=''  # 苹果不提供头像
            )
        except Exception as e:
            logger.exception("解析苹果ID令牌失败")
            return Response(api_response(
                code=400,
                message=f'解析苹果ID令牌失败: {str(e)}',
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)

    def _generate_apple_client_secret(self, provider):
        """生成苹果客户端密钥"""
        try:
            # 获取必要的参数
            team_id = provider.team_id
            client_id = provider.client_id
            key_id = provider.key_id
            private_key = provider.private_key
            
            # 如果没有直接提供私钥，尝试从文件读取
            if not private_key and provider.private_key_path:
                try:
                    private_key = provider.private_key_path.read().decode('utf-8')
                except Exception as e:
                    logger.error(f"读取苹果私钥文件失败: {str(e)}")
                    raise ValueError(f"读取苹果私钥文件失败: {str(e)}")
            
            if not all([team_id, client_id, key_id, private_key]):
                raise ValueError("苹果登录配置不完整")
            
            # 生成JWT
            now = int(time.time())
            expiry = now + 86400 * 180  # 180天
            
            headers = {
                'kid': key_id
            }
            
            payload = {
                'iss': team_id,
                'iat': now,
                'exp': expiry,
                'aud': 'https://appleid.apple.com',
                'sub': client_id
            }
            
            # 生成并返回JWT
            return jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
        except Exception as e:
            logger.exception("生成苹果客户端密钥失败")
            raise ValueError(f"生成苹果客户端密钥失败: {str(e)}")
    
    def _get_or_create_user(self, provider, provider_user_id, access_token, refresh_token, expires_in, user_data, username, email, nickname, avatar):
        """
        查找或创建用户，并关联OAuth账号
        """
        # 计算令牌过期时间
        expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
        
        # 查找是否已有关联的OAuth账号
        try:
            oauth = UserOAuth.objects.get(provider=provider, provider_user_id=provider_user_id)
            user = oauth.user
            
            # 更新OAuth账号信息
            oauth.access_token = access_token
            oauth.refresh_token = refresh_token
            oauth.expires_at = expires_at
            oauth.raw_data = user_data
            oauth.save()
            
            # 更新用户信息
            if nickname and not user.nickname:
                user.nickname = nickname
            if avatar and not user.avatar:
                user.avatar = avatar
            
            # 更新登录统计
            user.login_count += 1
            user.last_login = timezone.now()
            if hasattr(self.request, 'META'):
                x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    user.last_login_ip = x_forwarded_for.split(',')[0]
                else:
                    user.last_login_ip = self.request.META.get('REMOTE_ADDR')
            
            user.save()
            
        except UserOAuth.DoesNotExist:
            # 创建新用户
            # 检查邮箱是否已被使用
            if email and User.objects.filter(email=email).exists():
                # 如果邮箱已被使用，尝试使用该邮箱的用户
                user = User.objects.get(email=email)
            else:
                # 确保用户名唯一
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # 创建新用户
                user_manager = UserManager()
                random_password = user_manager.make_random_password()

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=random_password,
                    nickname=nickname,
                    avatar=avatar,
                    is_verified=True  # 第三方登录的用户视为已验证
                )
            
            # 创建OAuth关联
            oauth = UserOAuth.objects.create(
                user=user,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                raw_data=user_data
            )
        
        # 获取或创建令牌
        token, created = Token.objects.get_or_create(user=user)
        
        # 返回用户信息和令牌
        return Response(api_response(
            code=200,
            message=_('登录成功'),
            data={
                'token': token.key,
                'user': UserSerializer(user).data
            }
        ))

@api_view(['POST'])
@permission_classes([AllowAny])
def social_login(request):
    """
    社交登录API
    """
    provider = request.data.get('provider')
    code = request.data.get('code')
    redirect_uri = request.data.get('redirect_uri')
    app_id = request.data.get('app_id', 'default')  # 添加 app_id 参数
    
    if not provider or not code:
        return Response(api_response(
            code=400,
            message='缺少必要参数',
            data={'detail': 'provider 和 code 是必需的'}
        ), status=status.HTTP_400_BAD_REQUEST)
    
    # 创建视图实例
    view = SocialLoginView()
    view.request = request
    
    # 准备数据
    data = {
        'provider': provider,
        'code': code,
        'app_id': app_id  # 添加 app_id
    }
    if redirect_uri:
        data['redirect_uri'] = redirect_uri
    
    # 创建序列化器
    serializer = SocialLoginSerializer(data=data)
    if not serializer.is_valid():
        return Response(api_response(
            code=400,
            message='参数验证失败',
            data=serializer.errors
        ), status=status.HTTP_400_BAD_REQUEST)
    
    # 调用视图的post方法
    return view.post(request)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    用户注册
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # 创建认证令牌
        token, created = Token.objects.get_or_create(user=user)
        
        return Response(api_response(
            code=200,
            message='注册成功',
            data={
                'token': token.key,
                'user': UserSerializer(user).data
            }
        ), status=status.HTTP_201_CREATED)
    
    return Response(api_response(
        code=400,
        message='注册失败',
        data=serializer.errors
    ), status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """
    验证邮箱
    """
    email = request.data.get('email')
    code = request.data.get('code')
    
    if not email or not code:
        return Response({
            'error': '缺少必要参数',
            'detail': '邮箱和验证码是必需的'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证验证码
    cache_key = f"verification_code_{email}"
    stored_code = cache.get(cache_key)
    
    if not stored_code or stored_code != code:
        return Response({
            'error': '验证失败',
            'detail': '验证码无效或已过期'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 激活用户
    try:
        user = User.objects.get(email=email, is_active=False)
        user.is_active = True
        user.is_verified = True
        user.save()
        
        # 清除缓存中的验证码
        cache.delete(cache_key)
        
        # 创建认证令牌
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'detail': _('邮箱验证成功'),
            'token': token.key,
            'user': UserSerializer(user).data
        })
    except User.DoesNotExist:
        return Response({
            'error': _('验证失败'),
            'detail': _('用户不存在或已激活')
        }, status=status.HTTP_400_BAD_REQUEST)

def send_verification_email(email, code):
    """
    发送验证邮件
    """
    subject = _('验证您的账号')
    message = _(f'您的验证码是: {code}，有效期为1小时。')
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
        }
    ),
    responses={
        200: openapi.Response('成功获取令牌', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                'msg': openapi.Schema(type=openapi.TYPE_STRING),
                'data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            }
        )),
        400: '用户名或密码错误'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def obtain_auth_token(request):
    """
    获取认证令牌
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(api_response(
            code=400,
            message='用户名和密码不能为空',
            data=None
        ), status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if not user:
        # 尝试使用邮箱登录
        try:
            user_obj = User.objects.get(email=username)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
    
    if not user:
        return Response(api_response(
            code=400,
            message='用户名或密码错误',
            data=None
        ), status=status.HTTP_400_BAD_REQUEST)
    
    if not user.is_active:
        return Response(api_response(
            code=400,
            message='用户已被禁用',
            data=None
        ), status=status.HTTP_400_BAD_REQUEST)
    
    # 更新登录统计
    user.login_count += 1
    user.last_login = timezone.now()
    
    # 记录IP地址
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        user.last_login_ip = x_forwarded_for.split(',')[0]
    else:
        user.last_login_ip = request.META.get('REMOTE_ADDR')
    
    user.save(update_fields=['login_count', 'last_login', 'last_login_ip'])
    
    # 获取或创建令牌
    token, created = Token.objects.get_or_create(user=user)
    
    return Response(api_response(
        code=200,
        message=_('登录成功'),
        data={'token': token.key}
    ))

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_available_languages(request):
    """获取可用的语言列表"""
    languages = [
        {'code': code, 'name': name}
        for code, name in settings.LANGUAGES
    ]
    return Response(api_response(
        code=200,
        message=_('获取成功'),
        data=languages
    ))

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_language(request):
    """设置用户偏好语言"""
    language = request.data.get('language')
    
    if not language or language not in [lang[0] for lang in settings.LANGUAGES]:
        return Response(api_response(
            code=400,
            message=_('不支持的语言'),
            data=None
        ), status=status.HTTP_400_BAD_REQUEST)
    
    # 更新用户语言偏好
    user = request.user
    user.language = language
    user.save(update_fields=['language'])
    
    # 更新当前会话的语言
    translation.activate(language)
    request.session[translation.LANGUAGE_SESSION_KEY] = language
    
    return Response(api_response(
        code=200,
        message=_('语言设置成功'),
        data={'language': language}
    ))
