from django.utils import timezone
import time

def api_response(code=200, message="成功", data=None):
    """
    统一API响应格式
    
    Args:
        code: 状态码，200表示成功，其他表示失败
        message: 响应消息
        data: 响应数据
    
    Returns:
        dict: 统一格式的响应字典
    """
    return {
        'code': code,
        'msg': message,
        'data': data or {}
    }

def datetime_to_timestamp(dt):
    """将 datetime 对象转换为毫秒级时间戳"""
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)