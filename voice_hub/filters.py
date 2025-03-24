import django_filters
from .models import Feedback


class FeedbackFilter(django_filters.FilterSet):
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Feedback
        fields = {
            'feedback_type': ['exact'],
            'platform': ['exact'],
            'app_id': ['exact', 'icontains'],
            'is_processed': ['exact'],
            'email': ['exact', 'icontains'],
        } 