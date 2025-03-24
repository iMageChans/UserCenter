from django.shortcuts import render
from rest_framework import viewsets, filters, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from .models import Feedback
from .serializers import FeedbackSerializer
from .filters import FeedbackFilter


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    反馈API视图集
    
    list: 获取反馈列表
    create: 创建新反馈
    retrieve: 获取单个反馈详情
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FeedbackFilter
    search_fields = ['content', 'email']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        创建反馈不需要认证，其他操作需要管理员权限
        """
        if self.action == 'create':
            return []
        return [permissions.IsAdminUser()]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'code': 200,
                'message': _('获取成功'),
                'data': {
                    'results': serializer.data,
                }
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': _('获取成功'),
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 200,
            'message': _('获取成功'),
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response({
                'code': 201,
                'message': _('反馈提交成功'),
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 400,
            'message': _('提交失败'),
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({
                'code': 200,
                'message': _('更新成功'),
                'data': serializer.data
            })
        return Response({
            'code': 400,
            'message': _('更新失败'),
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': _('删除成功'),
            'data': None
        }, status=status.HTTP_200_OK)
