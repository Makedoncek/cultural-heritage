from celery import shared_task
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User

signer = TimestampSigner()


# --- Email Verification ---

def make_email_verification_token(user):
    return signer.sign(str(user.pk))


def verify_email_token(token, max_age=86400):
    """Returns user_pk or None. max_age=24h."""
    try:
        user_pk = signer.unsign(token, max_age=max_age)
        return int(user_pk)
    except (BadSignature, SignatureExpired):
        return None


@shared_task
def send_verification_email(user_id):
    user = User.objects.get(pk=user_id)
    token = make_email_verification_token(user)
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_message = render_to_string('emails/verify_email.html', {
        'user': user,
        'verify_url': verify_url,
    })

    send_mail(
        subject='CultureMap — Підтвердження електронної пошти',
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


# --- Password Reset ---

def make_password_reset_token(user):
    """Returns (uid, token) pair."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def verify_password_reset_token(uidb64, token):
    """Returns User or None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None

    if default_token_generator.check_token(user, token):
        return user
    return None


@shared_task
def send_password_reset_email(user_id):
    user = User.objects.get(pk=user_id)
    uid, token = make_password_reset_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    html_message = render_to_string('emails/password_reset.html', {
        'user': user,
        'reset_url': reset_url,
    })

    send_mail(
        subject='CultureMap — Скидання пароля',
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


# --- Status Notification ---

@shared_task
def send_status_notification(obj_id, new_status):
    from .models import CulturalObject
    obj = CulturalObject.objects.select_related('author').get(pk=obj_id)

    template_map = {
        'approved': 'emails/object_approved.html',
    }
    template = template_map.get(new_status)
    if not template:
        return

    object_url = f"{settings.FRONTEND_URL}/objects/{obj.pk}"

    html_message = render_to_string(template, {
        'user': obj.author,
        'object': obj,
        'object_url': object_url,
    })

    subject_map = {
        'approved': f'CultureMap — Ваш об\'єкт «{obj.title}» затверджено',
    }

    send_mail(
        subject=subject_map[new_status],
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[obj.author.email],
        html_message=html_message,
    )
