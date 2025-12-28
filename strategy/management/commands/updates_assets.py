import asyncio
import ssl
import os
from typing import List

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import BaseCommand
from django.shortcuts import get_object_or_404
from t_tech.invest import AsyncClient, InstrumentStatus
from t_tech.invest.constants import INVEST_GRPC_API_SANDBOX

from strategy.models import AssetData, CheckAssets, Settings


class Command(BaseCommand):
    help = "Обновление базы акций"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = os.getenv('TOKEN', '')
        self.batch_size = 50  # Оптимальный размер батча для запросов

    async def get_all_assets(self) -> List:
        """Получение всех активов"""
        async with AsyncClient(self.token, target=INVEST_GRPC_API_SANDBOX) as client:
            api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            while api_request_counter >= 190:
                wait_time = 10
                await asyncio.sleep(wait_time)
                self.stdout.write(self.style.WARNING(f"Большое количество запросов ({api_request_counter}). Повторный запрос через {wait_time} секунд"))
                api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            response = await client.instruments.shares()
            cache.incr('API_REQUESTS_COUNTER')
        return response.instruments

    async def get_asset_values_batch(self, figi_list: List[str]) -> dict:
        """Получение цен для батча активов"""
        async with AsyncClient(self.token, target=INVEST_GRPC_API_SANDBOX) as client:
            api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            while api_request_counter >= 190:
                wait_time = 10
                await asyncio.sleep(wait_time)
                self.stdout.write(self.style.WARNING(f"Большое количество запросов ({api_request_counter}). Повторный запрос через {wait_time} секунд"))
                api_request_counter = cache.get('API_REQUESTS_COUNTER', 0)
            result = await client.market_data.get_last_prices(
                figi=figi_list,
                instrument_status=InstrumentStatus.INSTRUMENT_STATUS_ALL,
            )
            cache.incr('API_REQUESTS_COUNTER')
        return {price.figi: price.price for price in result.last_prices}

    async def process_assets(self, assets: List) -> List[AssetData]:
        """Асинхронная обработка активов с батчингом"""
        assets_to_add = []
        figi_to_asset = {}

        # Собираем все FIGI для батч-запросов
        figi_list = []
        for asset in assets:
            if not asset.ticker or not asset.figi:
                continue

            figi_list.append(asset.figi)
            figi_to_asset[asset.figi] = asset

        # Обрабатываем батчами
        for i in range(0, len(figi_list), self.batch_size):
            batch_figi = figi_list[i:i + self.batch_size]

            try:
                # Получаем цены для батча
                prices = await self.get_asset_values_batch(batch_figi)

                # Обрабатываем каждый актив в батче
                for figi in batch_figi:
                    if figi not in figi_to_asset:
                        continue

                    asset = figi_to_asset[figi]
                    price = prices.get(figi)

                    if not price:
                        self.stdout.write(
                            self.style.WARNING(f"Цена не найдена для {asset.ticker}")
                        )
                        continue

                    # Создаем объект AssetData
                    logo_url = None
                    if asset.brand and asset.brand.logo_name:
                        logo_url = f'https://invest-brands.cdn-tinkoff.ru/{asset.brand.logo_name[:-4]}x160.png'

                    assets_to_add.append(AssetData(
                        ticker=asset.ticker,
                        class_code=asset.class_code,
                        nano=price.nano,
                        units=price.units,
                        logo_url=logo_url
                    ))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Ошибка при обработке батча {i}: {e}")
                )
                # Продолжаем обработку следующих батчей

        return assets_to_add

    @staticmethod
    def notifier():
        assets = CheckAssets.objects.all()

        for asset in assets:
            if asset.get_is_can_sold() or asset.get_is_danger():
                chat_id = Settings.objects.filter(owner=get_object_or_404(User, pk=asset.owner.pk)).first().tg_id
                if chat_id:
                    params = {
                        "chat_id": chat_id,
                        "text": f'Акцию {asset.ticker} можно продать!',
                    }

                    request = requests.get(
                        f"https://{settings.TELEGRAM_URL}bot{settings.TELEGRAM_TOKEN}/sendMessage", params=params
                    )
                    if request.status_code == 200:
                        asset.is_notified = True
                        asset.save()
            elif asset.is_notified:
                    asset.is_notified = False
                    asset.save()

    def handle(self, *args, **options):
        # Отключаем проверку SSL для избежания проблем с сертификатами
        ssl._create_default_https_context = ssl._create_unverified_context

        if not self.token:
            self.stdout.write(self.style.ERROR("TOKEN не найден в переменных окружения"))
            return

        self.stdout.write("Начало обновления базы акций...")

        try:
            # Получаем все активы
            self.stdout.write("Получение списка акций...")
            assets = asyncio.run(self.get_all_assets())

            if not assets:
                self.stdout.write(self.style.WARNING("Активы не найдены"))
                return

            self.stdout.write(f"Найдено {len(assets)} акций")

            # Обрабатываем активы
            self.stdout.write("Получение цен и обработка данных...")
            assets_to_add = asyncio.run(self.process_assets(assets))

            # Обновляем базу данных
            self.stdout.write("Обновление базы данных...")

            # Используем транзакцию для атомарности
            from django.db import transaction

            with transaction.atomic():
                # Удаляем старые данные
                deleted_count, _ = AssetData.objects.all().delete()
                self.stdout.write(f"Удалено {deleted_count} старых записей")

                # Добавляем новые данные
                created_count = len(AssetData.objects.bulk_create(assets_to_add))
                self.stdout.write(f"Добавлено {created_count} новых записей")

            self.stdout.write(
                self.style.SUCCESS(f"База акций успешно обновлена! Всего записей: {created_count}")
            )
            self.notifier()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при выполнении команды: {e}"))
