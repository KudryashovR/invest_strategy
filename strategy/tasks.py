from celery import shared_task
from django.core.management import call_command


@shared_task
def updates_assets():
    try:
        call_command('updates_assets')
        return "Command executed successfully"
    except Exception as e:
        print(f"Error executing command: {e}")
        raise

@shared_task
def reset_counter():
    try:
        call_command('reset_counter')
        return "Command executed successfully"
    except Exception as e:
        print(f"Error executing command: {e}")
        raise
