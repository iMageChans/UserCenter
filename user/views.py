import json
import time
import uuid
from django.utils.crypto import get_random_string

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
    SocialLoginSerializer, UserRegistrationSerializer, UserPremiumStatusSerializer,
    AnonymousUserConversionSerializer
)

User = get_user_model()
logger = logging.getLogger('user')

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

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        用户注销
        删除当前用户的认证令牌
        """
        try:
            # 删除用户的认证令牌
            request.user.auth_token.delete()

            return Response(api_response(
                code=200,
                message=_('注销成功'),
                data=None
            ))
        except Exception as e:
            logger.exception("用户注销失败")
            return Response(api_response(
                code=500,
                message=_('注销失败: {}').format(str(e)),
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def delete_account(self, request):
        """
        彻底删除用户账号
        只能由用户本人或管理员操作
        """
        try:
            # 获取用户
            user = request.user

            # 删除用户的认证令牌
            Token.objects.filter(user=user).delete()

            # 删除用户的OAuth关联
            UserOAuth.objects.filter(user=user).delete()

            # 记录用户删除操作
            logger.info(f"用户 {user.username} (ID: {user.id}) 已请求删除账号")

            # 删除用户
            user.delete()

            return Response(api_response(
                code=200,
                message=_('账号已成功删除'),
                data=None
            ))
        except Exception as e:
            logger.exception("删除用户账号失败")
            return Response(api_response(
                code=500,
                message=_('删除账号失败: {}').format(str(e)),
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def update_premium_status(self, request, pk=None):
        try:
            # 直接查询用户，避免使用 get_object() 可能引入的过滤
            try:
                user = User.objects.get(pk=pk)
            except User.DoesNotExist:
                return Response(api_response(
                    code=404,
                    message=_('用户不存在'),
                    data=None
                ), status=status.HTTP_404_NOT_FOUND)
            
            current_time = timezone.now()

            # 替换print为日志记录
            logger.info("请求数据: %s", request.data)
            logger.info("更新前的用户信息: id=%s, is_premium=%s, premium_expiry=%s", 
                        user.id, user.is_premium, user.premium_expiry)

            # 使用专用序列化器处理请求数据
            serializer = UserPremiumStatusSerializer(data=request.data, partial=True)

            if serializer.is_valid():
                logger.info("验证后的数据: %s", serializer.validated_data)

                # 检查premium_expiry和is_premium的关系
                if 'premium_expiry' in serializer.validated_data:
                    expiry_date = serializer.validated_data['premium_expiry']
                    
                    if expiry_date is not None:
                        # 检查过期时间是否在当前时间之后
                        if expiry_date > current_time:
                            user.is_premium = True
                        else:
                            # 如果过期时间已经过了，设置为非会员
                            user.is_premium = False
                        user.premium_expiry = expiry_date
                    else:
                        # 如果过期时间为None，根据请求中的is_premium决定
                        user.premium_expiry = None
                        if 'is_premium' in serializer.validated_data:
                            user.is_premium = serializer.validated_data['is_premium']
                        else:
                            user.is_premium = False
                elif 'is_premium' in serializer.validated_data:
                    # 如果只更新is_premium
                    user.is_premium = serializer.validated_data['is_premium']
                    # 如果设置为非会员，清除过期时间
                    if not user.is_premium:
                        user.premium_expiry = None
                    # 如果设置为会员但没有过期时间，检查现有过期时间是否有效
                    elif user.premium_expiry is not None and user.premium_expiry <= current_time:
                        # 如果现有过期时间已过期，则清除
                        user.premium_expiry = None
                        user.is_premium = False

                # 保存用户
                user.save()

                # 确认更新
                user.refresh_from_db()
                logger.info("更新后的用户信息: id=%s, is_premium=%s, premium_expiry=%s", 
                           user.id, user.is_premium, user.premium_expiry)

                # 返回更新后的用户信息
                user_serializer = UserSerializer(user)
                return Response(api_response(
                    code=200,
                    message=_('用户付费状态更新成功'),
                    data=user_serializer.data
                ))
            else:
                logger.error("验证错误: %s", serializer.errors)
                return Response(api_response(
                    code=400,
                    message=_('参数验证失败'),
                    data=serializer.errors
                ), status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("更新用户付费状态失败: %s", str(e))
            return Response(api_response(
                code=500,
                message=_('更新用户付费状态失败: {}').format(str(e)),
                data=None
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
        # 移除这些导入，因为不再需要
        # import sys
        import traceback
        
        # 使用日志记录而不是 sys.stdout.write
        logger.info("========= Apple login attempt =========")
        logger.info("Code: %s... (truncated)", code[:10])
        logger.info("Redirect URI: %s", redirect_uri)
        
        # 获取访问令牌
        token_url = 'https://appleid.apple.com/auth/token'
        
        # 使用数据库中的配置
        client_id = provider.client_id
        
        try:
            client_secret = self._generate_apple_client_secret(provider)
            logger.info("客户端密钥生成成功")
        except Exception as e:
            logger.error("生成客户端密钥失败: %s", str(e))
            logger.error(traceback.format_exc())
            return Response(api_response(
                code=500,
                message=f'生成苹果客户端密钥失败: {str(e)}',
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 获取重定向URI
        redirect_uri = redirect_uri or provider.redirect_uri
        
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        logger.info("Client ID: %s", client_id)
        logger.info("Redirect URI used: %s", redirect_uri)
        
        try:
            logger.info("正在发送请求到Apple授权服务器...")
            
            # 设置超时和额外的headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; YourApp/1.0)',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            token_response = requests.post(
                token_url, 
                data=token_data, 
                headers=headers,
                timeout=30
            )
            
            logger.info("Apple response status: %s", token_response.status_code)
            logger.debug("Apple response content: %s", token_response.text[:1000])
            
            # 尝试解析JSON响应
            try:
                token_result = token_response.json()
            except json.JSONDecodeError as e:
                logger.error("JSON解析失败: %s", str(e))
                logger.error("原始响应内容: %s", token_response.text)
                return Response(api_response(
                    code=400,
                    message=f'苹果授权响应解析失败: {str(e)}',
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            if 'error' in token_result:
                error_msg = f"苹果授权失败: {token_result.get('error_description', token_result['error'])}"
                logger.error("ERROR: %s", error_msg)
                return Response(api_response(
                    code=400,
                    message=error_msg,
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 解析ID令牌以获取用户信息
            id_token = token_result.get('id_token')
            if not id_token:
                logger.error("错误: 未获取到ID令牌")
                return Response(api_response(
                    code=400,
                    message='苹果登录失败: 未获取到ID令牌',
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 尝试不同的方式解码JWT
            logger.info("正在解析ID令牌...")
            
            try:
                # 1. 使用PyJWT解码
                jwt_payload = jwt.decode(id_token, options={"verify_signature": False})
                logger.info("JWT解析成功: %s", jwt_payload)
            except Exception as jwt_error:
                logger.error("PyJWT解析失败: %s", str(jwt_error))
                
                try:
                    # 2. 尝试手动解析Base64部分
                    import base64
                    token_parts = id_token.split('.')
                    if len(token_parts) >= 2:
                        # 处理填充
                        payload = token_parts[1]
                        payload += '=' * (4 - len(payload) % 4) if len(payload) % 4 else ''
                        decoded = base64.b64decode(payload)
                        jwt_payload = json.loads(decoded)
                        logger.info("手动解析JWT成功: %s", jwt_payload)
                    else:
                        raise Exception("JWT格式无效")
                except Exception as manual_error:
                    logger.error("手动解析JWT也失败: %s", str(manual_error))
                    return Response(api_response(
                        code=400,
                        message=f'解析苹果ID令牌失败: {str(jwt_error)}',
                        data=None
                    ), status=status.HTTP_400_BAD_REQUEST)
            
            # 获取用户标识符
            user_id = jwt_payload.get('sub')
            if not user_id:
                logger.error("错误: 未获取到用户标识符")
                return Response(api_response(
                    code=400,
                    message='苹果登录失败: 未获取到用户标识符',
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 获取邮箱和姓名
            email = jwt_payload.get('email', '')
            logger.info("用户邮箱: %s", email)
            
            # 记录请求中的所有字段用于调试
            logger.debug("请求体中的所有字段: %s", self.request.data)
            
            # 用户名可能在请求体的user字段中
            user_data = {}
            if 'user' in self.request.data:
                try:
                    user_info = self.request.data['user']
                    
                    # 处理可能的字符串或对象
                    if isinstance(user_info, str):
                        try:
                            user_info = json.loads(user_info)
                            logger.info("成功将user字段从字符串解析为JSON: %s", user_info)
                        except json.JSONDecodeError:
                            logger.warning("无法解析user字符串: %s", user_info)
                    
                    # 处理可能的各种格式的name字段
                    name = user_info.get('name', {})
                    logger.debug("解析到的name字段: %s, 类型: %s", name, type(name))
                    
                    nickname = ""
                    if isinstance(name, dict):
                        first_name = name.get('firstName', '')
                        last_name = name.get('lastName', '')
                        nickname = f"{first_name} {last_name}".strip()
                    elif isinstance(name, str):
                        nickname = name
                    
                    if not nickname:
                        nickname = "Apple User"
                    
                    user_data = {
                        'name': nickname,
                        'email': email
                    }
                    logger.info("最终用户数据: %s", user_data)
                except Exception as e:
                    logger.exception("解析用户信息时发生异常: %s", str(e))
                    # 使用默认值
                    user_data = {
                        'name': 'Apple User',
                        'email': email
                    }
            else:
                logger.info("请求体中没有user字段")
                user_data = {
                    'name': 'Apple User',
                    'email': email
                }
            
            # 查找或创建用户
            logger.info("准备创建或查找用户: id=%s, email=%s", user_id, email)
            
            return self._get_or_create_user(
                provider=provider,
                provider_user_id=user_id,
                access_token=token_result.get('access_token', ''),
                refresh_token=token_result.get('refresh_token', ''),
                expires_in=token_result.get('expires_in'),
                user_data=user_data,
                username=f"apple_{user_id}",
                email=email,
                nickname=user_data.get('name', 'Apple User'),
                avatar=''  # 苹果不提供头像
            )
        except requests.RequestException as e:
            logger.exception("网络请求错误: %s", str(e))
            error_msg = f"与苹果服务器通信失败: {str(e)}"
            return Response(api_response(
                code=500,
                message=error_msg,
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception("处理苹果登录时出现未预期的错误: %s", str(e))
            error_msg = f"苹果登录处理失败: {str(e)}"
            return Response(api_response(
                code=500,
                message=error_msg,
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_apple_client_secret(self, provider):
        """生成苹果客户端密钥"""
        try:
            # 获取必要的参数
            team_id = provider.team_id
            client_id = provider.client_id
            key_id = provider.key_id
            private_key = provider.private_key
            
            # 记录关键参数（不包含敏感信息）
            logger.info(f"生成Apple客户端密钥: team_id={team_id}, client_id={client_id}, key_id={key_id}")
            
            # 如果没有直接提供私钥，尝试从文件读取
            if not private_key and provider.private_key_path:
                try:
                    logger.info(f"从文件读取私钥: {provider.private_key_path}")
                    private_key = provider.private_key_path.read().decode('utf-8')
                except Exception as e:
                    logger.error(f"读取苹果私钥文件失败: {str(e)}")
                    raise ValueError(f"读取苹果私钥文件失败: {str(e)}")
            
            if not all([team_id, client_id, key_id, private_key]):
                missing = []
                if not team_id: missing.append('team_id')
                if not client_id: missing.append('client_id')
                if not key_id: missing.append('key_id')
                if not private_key: missing.append('private_key')
                error_msg = f"苹果登录配置不完整，缺少: {', '.join(missing)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 生成JWT
            now = int(time.time())
            expiry = now + 86400 * 180  # 180天
            
            headers = {
                'kid': key_id,
                'alg': 'ES256'  # 显式指定算法
            }
            
            payload = {
                'iss': team_id,
                'iat': now,
                'exp': expiry,
                'aud': 'https://appleid.apple.com',
                'sub': client_id
            }
            
            # 生成并返回JWT
            logger.info("正在生成JWT客户端密钥")
            client_secret = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
            logger.info("JWT客户端密钥生成成功")
            return client_secret
        except Exception as e:
            logger.exception(f"生成苹果客户端密钥失败: {str(e)}")
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
        
        # 添加日志记录
        logger.info("新用户注册成功: username=%s, email=%s", user.username, user.email)
        
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
    
    # 添加日志记录
    logger.warning("用户注册失败: %s", serializer.errors)
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
        logger.warning("登录尝试失败: 用户名或密码为空")
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
        # 不泄露具体哪个字段错误
        logger.warning("登录失败: 用户名或密码错误 (尝试用户名: %s)", username)
        return Response(api_response(
            code=400,
            message='用户名或密码错误',
            data=None
        ), status=status.HTTP_400_BAD_REQUEST)
    
    if not user.is_active:
        logger.warning("登录尝试: 用户已被禁用 (username: %s)", username)
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
    
    logger.info("用户登录成功: username=%s, IP=%s", username, user.last_login_ip)
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

class AnonymousUserViewSet(viewsets.ViewSet):
    """
    匿名用户视图集
    提供匿名登录和转正功能
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        匿名登录
        为未注册用户创建临时账号
        """
        try:
            # 生成唯一用户名
            username = f"anon_{uuid.uuid4().hex[:12]}"
            
            # 生成随机密码
            password = get_random_string(16)
            
            # 创建匿名用户
            user = User.objects.create_user(
                username=username,
                password=password,
                is_anonymous_user=True,
                nickname="username",
            )
            
            # 创建认证令牌
            token, created = Token.objects.get_or_create(user=user)
            
            # 记录登录信息
            user.login_count = 1
            user.last_login = timezone.now()
            
            # 记录IP地址
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                user.last_login_ip = x_forwarded_for.split(',')[0]
            else:
                user.last_login_ip = request.META.get('REMOTE_ADDR')
            
            user.save()
            
            # 返回用户信息和令牌
            return Response(api_response(
                code=200,
                message=_('匿名登录成功'),
                data={
                    'token': token.key,
                    'user': UserSerializer(user).data
                }
            ))
        except Exception as e:
            logger.exception("匿名登录失败")
            return Response(api_response(
                code=500,
                message=_('匿名登录失败: {}').format(str(e)),
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def convert(self, request):
        """
        将匿名用户转换为正式用户
        支持两种方式：
        1. 用户名密码注册
        2. 第三方账号绑定
        """
        user = request.user
        
        # 检查是否为匿名用户
        if not hasattr(user, 'is_anonymous_user') or not user.is_anonymous_user:
            return Response(api_response(
                code=400,
                message=_('只有匿名用户可以转换为正式用户'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 验证请求数据
        serializer = AnonymousUserConversionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(api_response(
                code=400,
                message=_('参数验证失败'),
                data=serializer.errors
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 获取验证后的数据
        validated_data = serializer.validated_data
        
        # 判断转换方式
        if 'username' in validated_data and 'password' in validated_data:
            # 用户名密码方式
            return self._convert_with_username_password(user, validated_data)
        else:
            # 第三方账号方式
            return self._convert_with_oauth(user, request, validated_data)
    
    def _convert_with_username_password(self, user, data):
        """使用用户名密码转换匿名用户"""
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return Response(api_response(
                code=400,
                message=_('用户名已被使用'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 检查邮箱是否已存在
        if email and User.objects.filter(email=email).exclude(id=user.id).exists():
            return Response(api_response(
                code=400,
                message=_('邮箱已被使用'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 更新用户信息
            user.username = username
            user.email = email if email else user.email
            user.set_password(password)
            user.is_anonymous_user = False
            user.save()
            
            # 重新生成令牌
            user.auth_token.delete()
            token, created = Token.objects.get_or_create(user=user)
            
            return Response(api_response(
                code=200,
                message=_('账号转换成功'),
                data={
                    'token': token.key,
                    'user': UserSerializer(user).data
                }
            ))
        except Exception as e:
            logger.exception("匿名用户转换失败")
            return Response(api_response(
                code=500,
                message=_('账号转换失败: {}').format(str(e)),
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _convert_with_oauth(self, user, request, data):
        """使用第三方账号转换匿名用户"""
        provider_name = data.get('provider')
        code = data.get('code')
        redirect_uri = data.get('redirect_uri')
        app_id = data.get('app_id', 'default')
        
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
        
        # 创建社交登录视图实例
        social_login_view = SocialLoginView()
        social_login_view.request = request
        
        # 根据不同的提供商处理OAuth流程
        handler_method = getattr(social_login_view, f'handle_{provider_name}_login', None)
        if not handler_method:
            return Response(api_response(
                code=501,
                message=f'未实现的登录方式: {provider_name}',
                data=None
            ), status=status.HTTP_501_NOT_IMPLEMENTED)
        
        try:
            # 获取OAuth用户信息
            oauth_response = handler_method(provider, code, redirect_uri)
            
            # 检查是否成功
            if oauth_response.status_code != 200:
                return oauth_response
            
            # 获取OAuth用户
            oauth_data = oauth_response.data.get('data', {})
            oauth_user = oauth_data.get('user', {})
            oauth_token = oauth_data.get('token')
            
            if not oauth_user or not oauth_token:
                return Response(api_response(
                    code=400,
                    message=_('获取第三方账号信息失败'),
                    data=None
                ), status=status.HTTP_400_BAD_REQUEST)
            
            # 检查OAuth用户是否已存在
            oauth_user_id = oauth_user.get('id')
            if oauth_user_id and oauth_user_id != user.id:
                # 如果OAuth用户已存在且不是当前用户，则合并账号
                try:
                    oauth_user_obj = User.objects.get(id=oauth_user_id)
                    
                    # 将匿名用户的数据转移到OAuth用户
                    # 这里可以添加数据迁移逻辑，如转移用户创建的内容等
                    
                    # 删除匿名用户
                    user.delete()
                    
                    # 返回OAuth用户的信息
                    return Response(api_response(
                        code=200,
                        message=_('账号已合并'),
                        data={
                            'token': oauth_token,
                            'user': UserSerializer(oauth_user_obj).data
                        }
                    ))
                except User.DoesNotExist:
                    pass
            
            # 更新匿名用户信息
            user.is_anonymous_user = False
            
            # 如果OAuth返回了用户名，尝试更新
            if 'username' in oauth_user and oauth_user['username']:
                # 检查用户名是否已存在
                new_username = oauth_user['username']
                if not User.objects.filter(username=new_username).exclude(id=user.id).exists():
                    user.username = new_username
            
            # 如果OAuth返回了邮箱，尝试更新
            if 'email' in oauth_user and oauth_user['email']:
                # 检查邮箱是否已存在
                new_email = oauth_user['email']
                if not User.objects.filter(email=new_email).exclude(id=user.id).exists():
                    user.email = new_email
            
            # 更新其他信息
            if 'nickname' in oauth_user and oauth_user['nickname']:
                user.nickname = oauth_user['nickname']
            
            if 'avatar' in oauth_user and oauth_user['avatar']:
                user.avatar = oauth_user['avatar']
            
            user.is_verified = True  # 第三方登录视为已验证
            user.save()
            
            # 创建OAuth关联
            UserOAuth.objects.create(
                user=user,
                provider=provider,
                provider_user_id=oauth_user.get('provider_user_id', ''),
                access_token=oauth_token,
                refresh_token='',
                expires_at=None,
                raw_data=oauth_user
            )
            
            # 重新生成令牌
            user.auth_token.delete()
            token, created = Token.objects.get_or_create(user=user)
            
            return Response(api_response(
                code=200,
                message=_('账号转换成功'),
                data={
                    'token': token.key,
                    'user': UserSerializer(user).data
                }
            ))
        except Exception as e:
            logger.exception("匿名用户转换失败")
            return Response(api_response(
                code=500,
                message=_('账号转换失败: {}').format(str(e)),
                data=None
            ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
