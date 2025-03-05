from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.core.cache import cache
from unittest.mock import patch, MagicMock
import json

from .models import OAuthProvider, UserOAuth

User = get_user_model()

class UserAuthTests(TestCase):
    """用户认证相关测试"""
    
    def setUp(self):
        """测试前准备工作"""
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('token')
        
        # 创建测试用户
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            nickname='Test User'
        )
        
        # 测试用户数据
        self.user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'nickname': 'New User'
        }
        
        self.login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
    
    def test_user_registration(self):
        """测试用户注册"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '注册成功')
        self.assertIn('token', response.data['data'])
        self.assertIn('user', response.data['data'])
        
        # 验证用户是否创建成功
        self.assertTrue(
            User.objects.filter(username='newuser').exists()
        )
    
    def test_user_registration_password_mismatch(self):
        """测试密码不匹配的注册"""
        data = self.user_data.copy()
        data['confirm_password'] = 'wrongpassword'
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['msg'], '注册失败')
        self.assertIn('confirm_password', response.data['data'])
    
    def test_user_login(self):
        """测试用户登录"""
        response = self.client.post(self.login_url, self.login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '登录成功')
        self.assertIn('token', response.data['data'])
        
        # 验证令牌是否有效
        token = response.data['data']['token']
        self.assertTrue(
            Token.objects.filter(key=token, user=self.test_user).exists()
        )
    
    def test_user_login_invalid_credentials(self):
        """测试无效凭据登录"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['msg'], '用户名或密码错误')
    
    def test_authenticated_access(self):
        """测试认证访问"""
        # 获取令牌
        token, _ = Token.objects.get_or_create(user=self.test_user)
        
        # 设置认证头
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # 访问需要认证的端点
        me_url = reverse('user-me')
        response = self.client.get(me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '获取成功')
        self.assertEqual(response.data['data']['username'], 'testuser')
    
    def test_unauthenticated_access(self):
        """测试未认证访问"""
        # 访问需要认证的端点
        me_url = reverse('user-me')
        response = self.client.get(me_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EmailVerificationTests(TestCase):
    """邮箱验证测试"""
    
    def setUp(self):
        """测试前准备工作"""
        self.client = APIClient()
        self.verify_email_url = reverse('verify-email')
        
        # 创建未激活的测试用户
        self.test_user = User.objects.create_user(
            username='inactive',
            email='inactive@example.com',
            password='testpassword123',
            is_active=False
        )
        
        # 模拟缓存中的验证码
        self.verification_code = '123456'
        cache_key = f"verification_code_{self.test_user.email}"
        cache.set(cache_key, self.verification_code, timeout=3600)
    
    def test_email_verification_success(self):
        """测试邮箱验证成功"""
        data = {
            'email': self.test_user.email,
            'code': self.verification_code
        }
        
        response = self.client.post(self.verify_email_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)
        self.assertIn('token', response.data)
        
        # 验证用户是否已激活
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_active)
        self.assertTrue(self.test_user.is_verified)
    
    def test_email_verification_invalid_code(self):
        """测试无效验证码"""
        data = {
            'email': self.test_user.email,
            'code': 'wrong-code'
        }
        
        response = self.client.post(self.verify_email_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], '验证失败')
        
        # 验证用户仍未激活
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)


class OAuthTests(TestCase):
    """OAuth认证测试"""
    
    def setUp(self):
        """测试前准备工作"""
        self.client = APIClient()
        self.social_login_url = reverse('social-login')
        
        # 创建OAuth提供商
        self.wechat_provider = OAuthProvider.objects.create(
            name='wechat',
            display_name='微信',
            client_id='wx_client_id',
            client_secret='wx_client_secret',
            is_active=True
        )
        
        self.apple_provider = OAuthProvider.objects.create(
            name='apple',
            display_name='Apple',
            client_id='apple_client_id',
            client_secret='apple_client_secret',
            is_active=True
        )
    
    @patch('requests.get')
    def test_wechat_login(self, mock_get):
        """测试微信登录"""
        # 模拟微信API响应
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'wx_access_token',
            'refresh_token': 'wx_refresh_token',
            'openid': 'wx_user_id',
            'expires_in': 7200
        }
        
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            'openid': 'wx_user_id',
            'nickname': 'WX User',
            'headimgurl': 'http://example.com/avatar.jpg'
        }
        
        # 设置mock的返回值顺序
        mock_get.side_effect = [mock_token_response, mock_user_response]
        
        # 发送登录请求
        data = {
            'provider': 'wechat',
            'code': 'wx_auth_code'
        }
        
        response = self.client.post(self.social_login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '登录成功')
        self.assertIn('token', response.data['data'])
        self.assertIn('user', response.data['data'])
        
        # 验证用户是否创建
        self.assertTrue(
            User.objects.filter(username=f"wx_wx_user_id").exists()
        )
        
        # 验证OAuth关联是否创建
        user = User.objects.get(username=f"wx_wx_user_id")
        self.assertTrue(
            UserOAuth.objects.filter(
                user=user,
                provider=self.wechat_provider,
                provider_user_id='wx_user_id'
            ).exists()
        )
    
    @patch('requests.post')
    @patch('jwt.decode')
    def test_apple_login(self, mock_jwt_decode, mock_post):
        """测试苹果登录"""
        # 模拟Apple API响应
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'apple_access_token',
            'refresh_token': 'apple_refresh_token',
            'id_token': 'apple_id_token',
            'expires_in': 3600
        }
        
        mock_post.return_value = mock_token_response
        
        # 模拟JWT解码
        mock_jwt_decode.return_value = {
            'sub': 'apple_user_id',
            'email': 'apple_user@example.com'
        }
        
        # 发送登录请求
        data = {
            'provider': 'apple',
            'code': 'apple_auth_code',
            'redirect_uri': 'https://example.com/callback'
        }
        
        response = self.client.post(self.social_login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '登录成功')
        self.assertIn('token', response.data['data'])
        self.assertIn('user', response.data['data'])
        
        # 验证用户是否创建
        self.assertTrue(
            User.objects.filter(username=f"apple_apple_user_id").exists()
        )
        
        # 验证OAuth关联是否创建
        user = User.objects.get(username=f"apple_apple_user_id")
        self.assertTrue(
            UserOAuth.objects.filter(
                user=user,
                provider=self.apple_provider,
                provider_user_id='apple_user_id'
            ).exists()
        )
    
    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        data = {
            'provider': 'unsupported',
            'code': 'some_code'
        }
        
        response = self.client.post(self.social_login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertIn('不支持的登录方式', response.data['detail'])


class UserProfileTests(TestCase):
    """用户资料测试"""
    
    def setUp(self):
        """测试前准备工作"""
        self.client = APIClient()
        
        # 创建测试用户
        self.test_user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='testpassword123',
            nickname='Profile User'
        )
        
        # 获取令牌并设置认证
        self.token, _ = Token.objects.get_or_create(user=self.test_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # 设置URL
        self.me_url = reverse('user-me')
        self.change_password_url = reverse('user-change-password')
        self.oauth_accounts_url = reverse('user-oauth-accounts')
    
    def test_get_profile(self):
        """测试获取个人资料"""
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '获取成功')
        self.assertEqual(response.data['data']['username'], 'profileuser')
        self.assertEqual(response.data['data']['email'], 'profile@example.com')
        self.assertEqual(response.data['data']['nickname'], 'Profile User')
    
    def test_change_password(self):
        """测试修改密码"""
        data = {
            'old_password': 'testpassword123',
            'new_password': 'newpassword456'
        }
        
        response = self.client.post(self.change_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '密码修改成功')
        
        # 验证密码是否已更改
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.check_password('newpassword456'))
    
    def test_change_password_wrong_old_password(self):
        """测试使用错误的旧密码修改密码"""
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword456'
        }
        
        response = self.client.post(self.change_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 400)
        self.assertEqual(response.data['msg'], '原密码不正确')
        
        # 验证密码未更改
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.check_password('testpassword123'))
    
    def test_get_oauth_accounts(self):
        """测试获取关联的OAuth账号"""
        # 创建OAuth提供商
        provider = OAuthProvider.objects.create(
            name='test_provider',
            display_name='Test Provider',
            client_id='test_client_id',
            client_secret='test_client_secret',
            is_active=True
        )
        
        # 创建OAuth关联
        UserOAuth.objects.create(
            user=self.test_user,
            provider=provider,
            provider_user_id='test_user_id',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            expires_at=None
        )
        
        response = self.client.get(self.oauth_accounts_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['msg'], '获取成功')
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['provider']['name'], 'test_provider')
        self.assertEqual(response.data['data'][0]['provider_user_id'], 'test_user_id')
