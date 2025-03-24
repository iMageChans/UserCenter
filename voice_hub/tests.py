from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Feedback, FeedbackType, Platform


class FeedbackModelTest(TestCase):
    def test_create_feedback(self):
        feedback = Feedback.objects.create(
            email='test@example.com',
            feedback_type=FeedbackType.BUG,
            platform=Platform.IOS,
            app_id='com.example.app',
            content='测试反馈内容'
        )
        self.assertEqual(feedback.is_processed, False)
        self.assertEqual(feedback.feedback_type, FeedbackType.BUG)
        self.assertEqual(feedback.platform, Platform.IOS)


class FeedbackAPITest(APITestCase):
    def test_create_feedback(self):
        """测试创建反馈"""
        url = reverse('feedback-list')
        data = {
            'email': 'test@example.com',
            'feedback_type': FeedbackType.BUG,
            'platform': Platform.IOS,
            'app_id': 'com.example.app',
            'content': '测试反馈内容'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(Feedback.objects.get().content, '测试反馈内容')
    
    def test_list_feedback_requires_authentication(self):
        """测试列表查询需要认证"""
        url = reverse('feedback-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
