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
    """
    将datetime对象转换为时间戳（毫秒）
    
    Args:
        dt: datetime对象
    
    Returns:
        int: 时间戳（毫秒）
    """
    if not dt:
        return None
    return int(time.mktime(dt.timetuple()) * 1000) 