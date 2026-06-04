"""Authentication endpoints: registration, email verification, password reset."""
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..email import (
    send_password_reset_email, send_verification_email,
    verify_email_token, verify_password_reset_token,
)
from ..serializers import RegisterSerializer
from .schemas import (
    PASSWORD_RESET_CONFIRM_SCHEMA, PASSWORD_RESET_SCHEMA,
    REGISTER_SCHEMA, RESEND_VERIFICATION_SCHEMA, VERIFY_EMAIL_SCHEMA,
)


@REGISTER_SCHEMA
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        send_verification_email.delay(user.id)

        return Response({
            'message': _('Реєстрація успішна! Перевірте вашу електронну пошту для підтвердження.'),
        }, status=status.HTTP_201_CREATED)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@VERIFY_EMAIL_SCHEMA
@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'error': _('Токен не надано.')}, status=status.HTTP_400_BAD_REQUEST)

    user_pk = verify_email_token(token)
    if user_pk is None:
        return Response({'error': _('Недійсне або прострочене посилання.')}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return Response({'error': _('Користувача не знайдено.')}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({'message': _('Пошту вже підтверджено.')})

    user.is_active = True
    user.save(update_fields=['is_active'])
    return Response({'message': _('Пошту успішно підтверджено! Тепер ви можете увійти у свій аккаунт.')})


@PASSWORD_RESET_SCHEMA
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get('email', '').strip()
    if email:
        try:
            user = User.objects.get(email=email, is_active=True)
            send_password_reset_email.delay(user.id)
        except User.DoesNotExist:
            pass
    return Response({'message': _('Якщо цю адресу зареєстровано, ми надіслали лист із інструкціями.')})


@PASSWORD_RESET_CONFIRM_SCHEMA
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    password = request.data.get('password', '')
    password2 = request.data.get('password2', '')

    if not all([uid, token, password, password2]):
        return Response({'error': _('Усі поля є обов\'язковими.')}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return Response({'error': _('Паролі не збігаються.')}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({'error': _('Пароль має містити щонайменше 8 символів.')}, status=status.HTTP_400_BAD_REQUEST)

    user = verify_password_reset_token(uid, token)
    if user is None:
        return Response({'error': _('Недійсне або прострочене посилання.')}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save(update_fields=['password'])
    return Response({'message': _('Пароль успішно змінено!')})


@RESEND_VERIFICATION_SCHEMA
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    email = request.data.get('email', '').strip()
    if email:
        try:
            user = User.objects.get(email=email, is_active=False)
            send_verification_email.delay(user.id)
        except User.DoesNotExist:
            pass
    return Response(
        {'message': _('Якщо цю адресу електронної пошти зареєстровано, ми надіслали лист для підтвердження.')})
