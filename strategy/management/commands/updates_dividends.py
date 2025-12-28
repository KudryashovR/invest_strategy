import asyncio
import os
from datetime import datetime, time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import BaseCommand
from django.shortcuts import get_object_or_404
from t_tech.invest import AsyncClient
from t_tech.invest.constants import INVEST_GRPC_API_SANDBOX

from strategy.models import AssetData, Settings, AssetDividend


class Command(BaseCommand):
    help = "Обновление базы дивидендов"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID пользователя'
        )

    async def get_all_assets(self, token):
        async with AsyncClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
            api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            while api_request_counter >= 190:
                wait_time = 10
                await asyncio.sleep(wait_time)
                self.stdout.write(
                    self.style.WARNING(f"Большое количество запросов ({api_request_counter}). Повторный запрос через {wait_time} секунд"))
                api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            response = await client.instruments.shares()
            cache.incr('API_REQUESTS_COUNTER')
        return response.instruments

    async def get_dividends(self, token, figi, date_from, date_to):
        async with AsyncClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
            api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            while api_request_counter >= 190:
                wait_time = 10
                await asyncio.sleep(wait_time)
                self.stdout.write(
                    self.style.WARNING(
                        f"Большое количество запросов ({api_request_counter}). Повторный запрос через {wait_time} секунд"))
                api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            response = await client.instruments.get_dividends(
                figi=figi,
                from_=date_from,
                to=date_to
            )
            cache.incr('API_REQUESTS_COUNTER')
        return response.dividends

    def handle(self, *args, **options):
        user_id = options['user_id']
        user = get_object_or_404(User, pk=user_id)
        token = os.getenv('TOKEN', '')
        assets = asyncio.run(self.get_all_assets(token))
        self.stdout.write(
            self.style.WARNING(
                f"Собрано {len(assets)} акций"))
        figis = []
        dividends_to_add = []
        date_from = Settings.objects.filter(owner=user).first().dividends_from_date
        dt_from = datetime.combine(date_from, time.min)
        date_to = Settings.objects.filter(owner=user).first().dividends_to_date
        dt_to = datetime.combine(date_to, time.min)
        for asset in assets:
            price = AssetData.objects.filter(ticker=asset.ticker).first()
            curency = asset.currency
            if curency == 'rub':
                figis.append((asset.ticker, asset.figi, asset.name, price.get_price()))
        self.stdout.write(
            self.style.WARNING(
                f"Всего рублевых акций: {len(figis)}"))
        counter = 0
        for figi in figis:
            dividend = asyncio.run(self.get_dividends(token, figi[1], dt_from, dt_to))
            counter += 1
            if dividend and dividend[0].dividend_net.currency == 'rub':
                units = dividend[0].dividend_net.units
                nano = dividend[0].dividend_net.nano
                div_price = units + (nano / 1_000_000_000)
                profitability = div_price / figi[3] * 100
                check_date = dividend[0].last_buy_date.date()
                if date_from <= check_date <= date_to:
                    dividends_to_add.append(AssetDividend(
                        ticker=figi[0],
                        company_name=figi[2],
                        payday=dividend[0].last_buy_date,
                        dividend=div_price,
                        profitability=profitability,
                        price=figi[3],
                        owner=user
                    ))
        self.stdout.write(
            self.style.WARNING(
                f"Добавлено {len(dividends_to_add)} акций"))
        AssetDividend.objects.filter(owner=user).all().delete()
        AssetDividend.objects.bulk_create(dividends_to_add)
