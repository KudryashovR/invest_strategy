from datetime import date

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from strategy.models import Settings


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        Settings.objects.create(
            available_capital=4000,
            broker_commission=.015,
            dividend_tax=13,
            central_bank_rate=.165,
            dividends_from_date=date.today(),
            dividends_to_date=date.today(),
            tg_id=0,
            owner=instance
        )
