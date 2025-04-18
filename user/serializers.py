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
        fields = [
            'id', 'username', 'email', 'nickname', 'avatar',
            'is_verified', 'is_premium', 'premium_expiry',
            'language', 'timezone', 'is_anonymous_user',  # 添加匿名用户标识
            'created_at', 'updated_at', 'date_joined', 'last_login'  # 添加缺少的字段
        ]
        read_only_fields = ['id', 'is_verified', 'is_premium', 'premium_expiry', 'created_at', 'updated_at']

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
            raise serializers.ValidationError("两次输入的密码不一致")

        # 验证邮箱是否已被使用
        email = data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError("该邮箱已被注册")

        # 验证用户名是否已被使用
        username = data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError("该用户名已被使用")

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


class UserPremiumStatusSerializer(serializers.Serializer):
    """用户付费状态更新序列化器"""
    user_id = serializers.IntegerField(write_only=True, required=False)
    is_premium = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, write_only=True)

    class Meta:
        fields = ['user_id', 'is_premium', 'expires_at']


class AnonymousUserConversionSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    provider = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
    redirect_uri = serializers.URLField(required=False)
    app_id = serializers.CharField(required=False, default='default')

    def validate(self, data):
        """
        验证转换方式：用户名密码或第三方登录
        """
        # 检查是否提供了用户名密码
        has_username_password = 'username' in data and 'password' in data

        # 检查是否提供了第三方登录信息
        has_oauth = 'provider' in data and 'code' in data

        if not has_username_password and not has_oauth:
            raise serializers.ValidationError(
                "必须提供用户名和密码，或者第三方登录信息"
            )

        return data