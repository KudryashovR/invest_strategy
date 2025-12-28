import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invest_strategy.settings')

app = Celery('strategy')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
