from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import date

class CheckAssets(models.Model):
    ticker = models.CharField(max_length=10, verbose_name="Тикер")
    buy_price = models.FloatField(verbose_name='Цена покупки')
    buy_count = models.IntegerField(verbose_name='Количество')
    buy_date = models.DateField(default=timezone.now, verbose_name='Дата покупки')
    current_price = models.FloatField(verbose_name='Текущая цена')
    excepted_price = models.FloatField(verbose_name='Ожидаемая цена')
    is_notified = models.BooleanField(default=False, verbose_name="Проинформирована")
    owner = models.ForeignKey(User, default=1, on_delete=models.CASCADE, verbose_name='Пользователь')

    class Meta:
        verbose_name = "Контролируемая акция"
        verbose_name_plural = "Контролируемые акции"
        ordering = ['buy_date']

    def get_holding_time(self):
        today = date.today()
        month = (today.year - self.buy_date.year) * 12 + (today.month - self.buy_date.month)

        if month == 0:
            month = 1

        return month

    def set_current_price(self, value):
        self.current_price = value
        self.save()

    def get_price_diff(self):
        price_diff = (self.current_price - self.buy_price) * self.buy_count

        return price_diff

    def get_expected_price_by_key_rate(self):
        expected_price = self.buy_price + (self.buy_price * Settings.objects.get_queryset().first().central_bank_rate / self.get_holding_time())

        return expected_price

    def get_is_can_sold(self):
        if self.current_price > self.get_expected_price_by_key_rate() and self.current_price > self.excepted_price:
            return True
        else:
            return False

    def get_is_danger(self):
        if self.get_expected_price_by_key_rate() > self.excepted_price:
            return True
        else:
            return False

    def set_excepted_price(self, value):
        self.excepted_price = value
        self.save()

class AssetData(models.Model):
    ticker = models.CharField(max_length=10, verbose_name="Тикер")
    class_code = models.CharField(max_length=10, verbose_name="Секция торгов")
    nano = models.IntegerField(verbose_name='Дробная часть цены')
    units = models.IntegerField(verbose_name='Целая часть цены')
    logo_url = models.URLField(verbose_name="URL логотипа")

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def get_price(self):
        return self.units + (self.nano / 1_000_000_000)

class Settings(models.Model):
    available_capital = models.IntegerField(verbose_name='Доступный капитал (руб.)')
    broker_commission = models.FloatField(verbose_name='Комиссия брокера (%)')
    dividend_tax = models.FloatField(verbose_name='Налог на дивиденды (%)')
    central_bank_rate = models.FloatField(verbose_name='Ключевая ставка (%)')
    dividends_from_date = models.DateField(verbose_name="Дата старта отсечки дивидендов")
    dividends_to_date = models.DateField(verbose_name="Дата конца отсечки дивидендов")
    tg_id = models.IntegerField(verbose_name="ID пользователя ТГ для отправки сообщения")
    owner = models.ForeignKey(User, default=1, on_delete=models.CASCADE, verbose_name='Владелец')

    class Meta:
        verbose_name = "Настройка"
        verbose_name_plural = "Настройки"

class AssetDividend(models.Model):
    ticker = models.CharField(max_length=10, verbose_name="Тикер")
    company_name = models.CharField(max_length=255, verbose_name="Компания")
    payday = models.DateField(verbose_name="Дата отсечки")
    dividend = models.FloatField(verbose_name="Дивиденд (руб.)")
    profitability = models.FloatField(verbose_name="Доходность (%)")
    price = models.FloatField(verbose_name="Цена (руб.)")
    priority = models.IntegerField(null=True, blank=True, verbose_name="Приоритет")
    max_part = models.IntegerField(null=True, blank=True, verbose_name="Максимальная доля (%)")
    owner = models.ForeignKey(User, default=1, on_delete=models.CASCADE, verbose_name="Владелец")

    def __str__(self):
        return f'{self.ticker} - {self.payday} - {self.dividend}'

    class Meta:
        verbose_name = "Дивиденд"
        verbose_name_plural = "Дивиденды"
        ordering = ['-profitability']

class AssetCandidates(models.Model):
    ticker = models.CharField(max_length=10, verbose_name="Тикер")
    price = models.FloatField(verbose_name="Цена (руб.)")
    count = models.IntegerField(verbose_name="Количество")
    costs = models.FloatField(verbose_name="Затраты (руб.)")
    share = models.FloatField(verbose_name="Доля (%)")
    dividend = models.FloatField(verbose_name="Дивиденд (руб.)")
    owner = models.ForeignKey(User, default=1, on_delete=models.CASCADE, verbose_name="Владелец")

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"
