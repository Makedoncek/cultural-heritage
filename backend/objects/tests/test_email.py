from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status
from objects.email import (
    make_email_verification_token, verify_email_token,
    make_password_reset_token, verify_password_reset_token,
)

EMAIL_SETTINGS = {
    'CELERY_TASK_ALWAYS_EAGER': True,
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'FRONTEND_URL': 'http://testserver:3000',
}


class EmailVerificationTokenTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass123!')

    def test_token_roundtrip(self):
        token = make_email_verification_token(self.user)
        user_pk = verify_email_token(token)
        self.assertEqual(user_pk, self.user.pk)

    def test_expired_token(self):
        token = make_email_verification_token(self.user)
        result = verify_email_token(token, max_age=0)
        self.assertIsNone(result)

    def test_invalid_token(self):
        result = verify_email_token('garbage-token')
        self.assertIsNone(result)


class PasswordResetTokenTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass123!')

    def test_token_roundtrip(self):
        uid, token = make_password_reset_token(self.user)
        user = verify_password_reset_token(uid, token)
        self.assertEqual(user.pk, self.user.pk)

    def test_invalid_uid(self):
        _, token = make_password_reset_token(self.user)
        user = verify_password_reset_token('invalid', token)
        self.assertIsNone(user)

    def test_invalid_token(self):
        uid, _ = make_password_reset_token(self.user)
        user = verify_password_reset_token(uid, 'bad-token')
        self.assertIsNone(user)


@override_settings(**EMAIL_SETTINGS)
class RegisterWithVerificationTest(APITestCase):

    def test_register_sends_email_and_user_inactive(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertNotIn('tokens', response.data)

        user = User.objects.get(username='newuser')
        self.assertFalse(user.is_active)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Підтвердження', mail.outbox[0].subject)

    def test_inactive_user_cannot_login(self):
        User.objects.create_user('inactive', 'i@test.com', 'Pass123!', is_active=False)
        response = self.client.post('/api/auth/login/', {
            'username': 'inactive',
            'password': 'Pass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(**EMAIL_SETTINGS)
class VerifyEmailEndpointTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'Pass123!', is_active=False)

    def test_verify_valid_token(self):
        token = make_email_verification_token(self.user)
        response = self.client.get(f'/api/auth/verify-email/?token={token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_verify_invalid_token(self):
        response = self.client.get('/api/auth/verify-email/?token=bad-token')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_no_token(self):
        response = self.client.get('/api/auth/verify-email/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_already_active(self):
        self.user.is_active = True
        self.user.save()
        token = make_email_verification_token(self.user)
        response = self.client.get(f'/api/auth/verify-email/?token={token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('вже підтверджено', response.data['message'])


@override_settings(**EMAIL_SETTINGS)
class PasswordResetFlowTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'OldPass123!')

    def test_request_sends_email(self):
        response = self.client.post('/api/auth/password-reset/', {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Скидання', mail.outbox[0].subject)

    def test_request_nonexistent_email_still_200(self):
        response = self.client.post('/api/auth/password-reset/', {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirm_valid_token(self):
        uid, token = make_password_reset_token(self.user)
        response = self.client.post('/api/auth/password-reset/confirm/', {
            'uid': uid, 'token': token,
            'password': 'NewPass456!', 'password2': 'NewPass456!',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_confirm_password_mismatch(self):
        uid, token = make_password_reset_token(self.user)
        response = self.client.post('/api/auth/password-reset/confirm/', {
            'uid': uid, 'token': token,
            'password': 'NewPass456!', 'password2': 'Different!',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_invalid_token(self):
        uid, _ = make_password_reset_token(self.user)
        response = self.client.post('/api/auth/password-reset/confirm/', {
            'uid': uid, 'token': 'bad-token',
            'password': 'NewPass456!', 'password2': 'NewPass456!',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_short_password(self):
        uid, token = make_password_reset_token(self.user)
        response = self.client.post('/api/auth/password-reset/confirm/', {
            'uid': uid, 'token': token,
            'password': 'short', 'password2': 'short',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**EMAIL_SETTINGS)
class ResendVerificationTest(APITestCase):

    def test_resend_for_inactive_user(self):
        User.objects.create_user('inactive', 'i@test.com', 'Pass123!', is_active=False)
        response = self.client.post('/api/auth/resend-verification/', {'email': 'i@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_for_active_user_no_email(self):
        User.objects.create_user('active', 'a@test.com', 'Pass123!')
        response = self.client.post('/api/auth/resend-verification/', {'email': 'a@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_nonexistent_email_still_200(self):
        response = self.client.post('/api/auth/resend-verification/', {'email': 'nobody@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
