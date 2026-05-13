from smtplib import SMTPException

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

# Параметри retry для всіх email-task-ів: експоненційний backoff
# (1s → 2s → 4s → 8s → 16s, max 600s) з jitter — захист від SMTP flapping.
EMAIL_RETRY_KWARGS = dict(
    autoretry_for=(SMTPException, ConnectionError, OSError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)

signer = TimestampSigner()


def _user_language(user) -> str:
    """Return 'uk' or 'en' from the user's preference; default 'uk' if unset."""
    try:
        return user.preference.language
    except Exception:
        return 'uk'


def _template_for(name: str, lang: str) -> str:
    """Resolve email template name based on language. 'uk' uses the base name."""
    if lang == 'en':
        return f'emails/{name}_en.html'
    return f'emails/{name}.html'


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


VERIFY_SUBJECTS = {
    'uk': 'CultureMap — Підтвердження електронної пошти',
    'en': 'CultureMap — Email verification',
}


@shared_task(**EMAIL_RETRY_KWARGS)
def send_verification_email(user_id):
    user = User.objects.get(pk=user_id)
    token = make_email_verification_token(user)
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    lang = _user_language(user)

    html_message = render_to_string(_template_for('verify_email', lang), {
        'user': user,
        'verify_url': verify_url,
    })

    send_mail(
        subject=VERIFY_SUBJECTS.get(lang, VERIFY_SUBJECTS['uk']),
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


PASSWORD_RESET_SUBJECTS = {
    'uk': 'CultureMap — Скидання пароля',
    'en': 'CultureMap — Password reset',
}


@shared_task(**EMAIL_RETRY_KWARGS)
def send_password_reset_email(user_id):
    user = User.objects.get(pk=user_id)
    uid, token = make_password_reset_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    lang = _user_language(user)

    html_message = render_to_string(_template_for('password_reset', lang), {
        'user': user,
        'reset_url': reset_url,
    })

    send_mail(
        subject=PASSWORD_RESET_SUBJECTS.get(lang, PASSWORD_RESET_SUBJECTS['uk']),
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )


# --- Status Notification ---

def _approved_subject(lang: str, title: str) -> str:
    if lang == 'en':
        return f'CultureMap — Your object "{title}" has been approved'
    return f'CultureMap — Ваш об\'єкт «{title}» затверджено'


@shared_task(**EMAIL_RETRY_KWARGS)
def send_status_notification(obj_id, new_status):
    from .models import CulturalObject
    try:
        obj = CulturalObject.objects.select_related('author').get(pk=obj_id)
    except CulturalObject.DoesNotExist:
        return  # об'єкт видалено — старий task з черги

    if new_status != 'approved':
        return

    lang = _user_language(obj.author)
    object_url = f"{settings.FRONTEND_URL}/objects/{obj.pk}"

    html_message = render_to_string(_template_for('object_approved', lang), {
        'user': obj.author,
        'object': obj,
        'object_url': object_url,
    })

    send_mail(
        subject=_approved_subject(lang, obj.title),
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[obj.author.email],
        html_message=html_message,
    )


# --- Follower Notifications ---

def _follower_subject_and_labels(lang: str, author_username: str, obj_title: str, is_event: bool):
    if lang == 'en':
        type_label = 'event' if is_event else 'object'
        type_short = 'event' if is_event else 'object'
        subject = f'CultureMap — {author_username} published an {type_label} "{obj_title}"' if is_event \
            else f'CultureMap — {author_username} published an {type_label} "{obj_title}"'
        return subject, type_label, type_short
    type_label = 'подію' if is_event else 'об\'єкт'
    type_short = 'подія' if is_event else 'об\'єкт'
    subject = f'CultureMap — {author_username} опублікував(ла) {type_label} «{obj_title}»'
    return subject, type_label, type_short


INACCURACY_SUBJECTS = {
    'uk': {
        'resolved': 'CultureMap — Ваш репорт підтверджено',
        'dismissed': 'CultureMap — Ваш репорт відхилено',
    },
    'en': {
        'resolved': 'CultureMap — Your report has been confirmed',
        'dismissed': 'CultureMap — Your report has been dismissed',
    },
}

INACCURACY_OUTCOME_LABELS = {
    'uk': {'resolved': 'підтверджено', 'dismissed': 'відхилено'},
    'en': {'resolved': 'confirmed', 'dismissed': 'dismissed'},
}


@shared_task(**EMAIL_RETRY_KWARGS)
def send_inaccuracy_outcome_email(report_id):
    """Notify reporter when admin resolves or dismisses their report."""
    from .models import InaccuracyReport
    try:
        report = (InaccuracyReport.objects
                  .select_related('reporter', 'cultural_object')
                  .get(pk=report_id))
    except InaccuracyReport.DoesNotExist:
        return

    if report.status not in ('resolved', 'dismissed') or not report.reporter.email:
        return

    lang = _user_language(report.reporter)
    outcome = report.status
    subject = INACCURACY_SUBJECTS.get(lang, INACCURACY_SUBJECTS['uk'])[outcome]
    outcome_label = INACCURACY_OUTCOME_LABELS.get(lang, INACCURACY_OUTCOME_LABELS['uk'])[outcome]
    object_url = f"{settings.FRONTEND_URL}/objects/{report.cultural_object.pk}"

    html_message = render_to_string(_template_for('inaccuracy_resolved', lang), {
        'user': report.reporter,
        'object_title': report.cultural_object.title,
        'object_url': object_url,
        'reason_label': report.get_reason_type_display(),
        'outcome_label': outcome_label,
        'admin_response': report.admin_response,
    })

    send_mail(
        subject=subject,
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[report.reporter.email],
        html_message=html_message,
    )


@shared_task(**EMAIL_RETRY_KWARGS)
def send_follower_notifications(obj_id):
    """Розсилає підписникам автора лист про нову публікацію (об'єкт або подію).
    Кожному підписнику — у його обраній мові."""
    from .models import CulturalObject, FavoriteAuthor
    try:
        obj = CulturalObject.objects.select_related('author').get(pk=obj_id)
    except CulturalObject.DoesNotExist:
        return  # об'єкт видалено — старий task
    followers = (
        FavoriteAuthor.objects
        .filter(author=obj.author)
        .exclude(user=obj.author)
        .select_related('user', 'user__preference')
    )

    is_event = obj.object_type == CulturalObject.ObjectType.EVENT
    object_url = f"{settings.FRONTEND_URL}/objects/{obj.pk}"

    for fav in followers:
        user = fav.user
        if not user.email:
            continue
        lang = _user_language(user)
        subject, type_label, type_short = _follower_subject_and_labels(
            lang, obj.author.username, obj.title, is_event,
        )
        html_message = render_to_string(_template_for('follower_new_object', lang), {
            'follower': user,
            'author': obj.author,
            'object': obj,
            'object_url': object_url,
            'object_type_label': type_label,
            'object_type_short': type_short,
        })
        send_mail(
            subject=subject,
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
