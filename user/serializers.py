from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserOAuth, OAuthProvider
from .utils import datetime_to_timestamp

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    用户序列化器
    """
    date_joined = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    premium_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'nickname', 'avatar', 'phone',
                  'is_verified', 'language', 'timezone', 'date_joined',
                  'last_login', 'is_premium', 'premium_expiry')
        read_only_fields = ('id', 'date_joined', 'last_login', 'is_verified', 
                           'is_premium', 'premium_expiry')
    
    def get_date_joined(self, obj):
        return datetime_to_timestamp(obj.date_joined)
    
    def get_last_login(self, obj):
        return datetime_to_timestamp(obj.last_login)
        
    def get_premium_expiry(self, obj):
        return datetime_to_timestamp(obj.premium_expiry)

class OAuthProviderSerializer(serializers.ModelSerializer):
    """
    OAuth提供商序列化器
    """
    class Meta:
        model = OAuthProvider
        fields = ('id', 'name', 'is_active')

class UserOAuthSerializer(serializers.ModelSerializer):
    """
    用户OAuth账号序列化器
    """
    provider_name = serializers.CharField(source='provider.get_name_display', read_only=True)
    
    class Meta:
        model = UserOAuth
        fields = ('id', 'provider', 'provider_name', 'provider_user_id', 'created_at')
        read_only_fields = ('id', 'provider', 'provider_user_id', 'created_at')

class SocialLoginSerializer(serializers.Serializer):
    """
    社交登录序列化器
    """
    provider = serializers.CharField()
    code = serializers.CharField()
    redirect_uri = serializers.URLField(required=False)
    app_id = serializers.CharField(required=False, default='default')  # 添加 app_id 字段

class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'nickname', 'phone']
        extra_kwargs = {
            'email': {'required': True},
            'nickname': {'required': False}
        }
    
    def validate(self, data):
        # 验证两次密码是否一致
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError(_("两次输入的密码不一致"))
        
        # 验证邮箱是否已被使用
        email = data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("该邮箱已被注册"))
        
        # 验证用户名是否已被使用
        username = data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError(_("该用户名已被使用"))
        
        return data
    
    def create(self, validated_data):
        # 移除确认密码字段
        validated_data.pop('confirm_password', None)
        
        # 创建用户
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            nickname=validated_data.get('nickname', ''),
            phone=validated_data.get('phone', ''),
            is_active=validated_data.get('is_active', True),
            is_verified=validated_data.get('is_verified', True)
        )
        
        return user


class UserPremiumStatusSerializer(serializers.ModelSerializer):
    """用户付费状态更新序列化器"""
    user_id = serializers.IntegerField(write_only=True, required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, write_only=True)
    premium_expiry = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['user_id', 'is_premium', 'premium_expiry', 'expires_at']

    def validate(self, data):
        """验证数据并处理字段映射"""
        if 'is_premium' not in data:
            raise serializers.ValidationError({"is_premium": "缺少必要参数"})

        # 将expires_at映射到premium_expiry
        if 'expires_at' in data:
            print(f"expires_at: {data['expires_at']}")
            print(f"expires_at pop: {data.pop('expires_at')}")
            data['premium_expiry'] = data.pop('expires_at')

        # 移除user_id字段，因为它不是模型的一部分
        if 'user_id' in data:
            data.pop('user_id')

        return data