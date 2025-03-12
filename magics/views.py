from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.utils.translation import gettext as _
import logging
import random
import string

from .models import MagicCode, MagicCodeUsage
from .serializers import MagicCodeSerializer, MagicCodeUsageSerializer, RedeemCodeSerializer
from user.utils import api_response, datetime_to_timestamp

logger = logging.getLogger(__name__)

class MagicCodeViewSet(viewsets.ModelViewSet):
    """优惠码视图集"""
    queryset = MagicCode.objects.all()
    serializer_class = MagicCodeSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """根据查询参数过滤优惠码"""
        queryset = MagicCode.objects.all()
        
        # 按应用ID过滤
        app_id = self.request.query_params.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)
        
        # 按状态过滤
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def perform_create(self, serializer):
        """创建优惠码时设置创建者"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """生成单个优惠码"""
        app_id = request.data.get('app_id', 'default')
        days = request.data.get('days', 30)
        max_uses = request.data.get('max_uses', 1)
        prefix = request.data.get('prefix', '')
        expires_days = request.data.get('expires_days')
        
        # 生成优惠码
        code = MagicCode.generate_code(prefix=prefix)
        
        # 设置过期时间
        expires_at = None
        if expires_days:
            expires_at = timezone.now() + timezone.timedelta(days=int(expires_days))
        
        # 创建优惠码
        magic_code = MagicCode.objects.create(
            code=code,
            app_id=app_id,
            days=days,
            max_uses=max_uses,
            expires_at=expires_at,
            created_by=request.user
        )
        
        serializer = self.get_serializer(magic_code)
        return Response(api_response(
            code=200,
            message=_('优惠码生成成功'),
            data=serializer.data
        ))
    
    @action(detail=False, methods=['post'])
    def batch_generate(self, request):
        """批量生成优惠码"""
        app_id = request.data.get('app_id', 'default')
        days = request.data.get('days', 30)
        max_uses = request.data.get('max_uses', 1)
        count = request.data.get('count', 1)
        prefix = request.data.get('prefix', '')
        expires_days = request.data.get('expires_days')
        
        # 限制一次最多生成的数量
        if count > 100:
            return Response(api_response(
                code=400,
                message=_('一次最多生成100个优惠码'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 设置过期时间
        expires_at = None
        if expires_days:
            expires_at = timezone.now() + timezone.timedelta(days=int(expires_days))
        
        # 批量生成优惠码
        codes = []
        for _ in range(int(count)):
            code = MagicCode.generate_code(prefix=prefix)
            magic_code = MagicCode.objects.create(
                code=code,
                app_id=app_id,
                days=days,
                max_uses=max_uses,
                expires_at=expires_at,
                created_by=request.user
            )
            codes.append(magic_code)
        
        serializer = self.get_serializer(codes, many=True)
        return Response(api_response(
            code=200,
            message=_('批量生成优惠码成功'),
            data=serializer.data
        ))
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用优惠码"""
        magic_code = self.get_object()
        magic_code.status = 'disabled'
        magic_code.save(update_fields=['status'])
        
        serializer = self.get_serializer(magic_code)
        return Response(api_response(
            code=200,
            message=_('优惠码已禁用'),
            data=serializer.data
        ))
    
    @action(detail=True, methods=['get'])
    def usage_records(self, request, pk=None):
        """获取优惠码使用记录"""
        magic_code = self.get_object()
        usages = MagicCodeUsage.objects.filter(code=magic_code)
        
        serializer = MagicCodeUsageSerializer(usages, many=True)
        return Response(api_response(
            code=200,
            message=_('获取成功'),
            data=serializer.data
        ))

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def redeem_code(request):
    """兑换优惠码"""
    serializer = RedeemCodeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(api_response(
            code=400,
            message=_('无效的请求数据'),
            data=serializer.errors
        ), status=status.HTTP_400_BAD_REQUEST)
    
    code = serializer.validated_data['code']
    app_id = serializer.validated_data.get('app_id', 'default')
    
    try:
        # 查找优惠码
        magic_code = MagicCode.objects.get(code=code, app_id=app_id)
        
        # 检查用户是否已经使用过此优惠码
        if MagicCodeUsage.objects.filter(code=magic_code, user=request.user).exists():
            return Response(api_response(
                code=400,
                message=_('您已经使用过此优惠码'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
        
        # 使用优惠码
        if magic_code.use(request.user):
            return Response(api_response(
                code=200,
                message=_('优惠码兑换成功，已获得 {} 天会员权益').format(magic_code.days),
                data={
                    'days_added': magic_code.days,
                    'premium_expiry': datetime_to_timestamp(request.user.premium_expiry)
                }
            ))
        else:
            return Response(api_response(
                code=400,
                message=_('优惠码无效或已过期'),
                data=None
            ), status=status.HTTP_400_BAD_REQUEST)
    
    except MagicCode.DoesNotExist:
        return Response(api_response(
            code=404,
            message=_('优惠码不存在'),
            data=None
        ), status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"兑换优惠码失败: {str(e)}", exc_info=True)
        return Response(api_response(
            code=500,
            message=_('兑换优惠码失败'),
            data={'detail': str(e)}
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
