from rest_framework import serializers
from .models import MagicCode, MagicCodeUsage
from user.utils import datetime_to_timestamp

class MagicCodeSerializer(serializers.ModelSerializer):
    """优惠码序列化器"""
    expires_at = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    
    class Meta:
        model = MagicCode
        fields = ('id', 'code', 'app_id', 'days', 'max_uses', 'used_count', 
                  'status', 'expires_at', 'created_at', 'updated_at')
        read_only_fields = ('id', 'code', 'used_count', 'created_at', 'updated_at')
    
    def get_expires_at(self, obj):
        return datetime_to_timestamp(obj.expires_at)
    
    def get_created_at(self, obj):
        return datetime_to_timestamp(obj.created_at)
    
    def get_updated_at(self, obj):
        return datetime_to_timestamp(obj.updated_at)

class MagicCodeUsageSerializer(serializers.ModelSerializer):
    """优惠码使用记录序列化器"""
    code = serializers.CharField(source='code.code')
    username = serializers.CharField(source='user.username')
    used_at = serializers.SerializerMethodField()
    
    class Meta:
        model = MagicCodeUsage
        fields = ('id', 'code', 'username', 'used_at')
    
    def get_used_at(self, obj):
        return datetime_to_timestamp(obj.used_at)

class RedeemCodeSerializer(serializers.Serializer):
    """兑换优惠码序列化器"""
    code = serializers.CharField(max_length=20)
    app_id = serializers.CharField(max_length=100, required=False, default='default') 