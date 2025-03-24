from rest_framework import serializers
from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'email', 'feedback_type', 'platform', 'app_id', 'content', 'is_processed', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_processed'] 