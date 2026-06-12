import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'archive-expired-events-daily': {
        'task': 'objects.tasks.archive_expired_events',
        'schedule': crontab(hour=2, minute=0),
    },
    'cleanup-rejected-photos-daily': {
        'task': 'objects.tasks.cleanup_rejected_photos',
        'schedule': crontab(hour=3, minute=0),
    },
    'cleanup-rejected-audios-daily': {
        'task': 'objects.tasks.cleanup_rejected_audios',
        'schedule': crontab(hour=3, minute=30),
    },
    'cleanup-processed-inaccuracy-reports-weekly': {
        'task': 'objects.tasks.cleanup_processed_inaccuracy_reports',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),
    },
}
