import numpy as np
from django.contrib.auth.models import User

from django.core.management import BaseCommand
from django.shortcuts import get_object_or_404

from strategy.models import AssetDividend, Settings, AssetCandidates


class Command(BaseCommand):
    help = "Обновление базы дивидендов"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID пользователя'
        )

    @staticmethod
    def calculate_count(available_capital, max_part, price, dividend):
        part1 = np.floor((available_capital * max_part / 100) / price)

        part2 = np.floor((available_capital * 0.21 / 12) / dividend)

        result = min(part1, part2)

        return int(result)

    @staticmethod
    def calculate_costs(price, count, broker_commission):
        result = price * count * (1 + broker_commission / 100 * 2)

        return float(result)

    @staticmethod
    def calculate_share(costs, available_capital):
        result = costs / available_capital * 100

        return float(result)

    @staticmethod
    def calculate_dividends(count, dividend, dividend_tax):
        result = count * dividend * (1 - dividend_tax / 100)

        return float(result)

    def handle(self, *args, **options):
        user_id = options['user_id']
        user = get_object_or_404(User, pk=user_id)
        assets = AssetDividend.objects.filter(owner=user).all()
        available_capital = Settings.objects.filter(owner=user).first().available_capital
        broker_commision = Settings.objects.filter(owner=user).first().broker_commission
        dividend_tax = Settings.objects.filter(owner=user).first().dividend_tax
        assets_to_add = []

        for asset in assets:
            ticker = asset.ticker
            price = asset.price
            max_part = asset.max_part

            if max_part:
                dividend = asset.dividend
                count = self.calculate_count(int(available_capital), int(max_part), float(price), float(dividend))
                costs =self.calculate_costs(float(price), count, float(broker_commision))
                share = self.calculate_share(costs, int(available_capital))
                dividend = self.calculate_dividends(count, float(dividend), float(dividend_tax))
                assets_to_add.append(AssetCandidates(
                    ticker=ticker,
                    price=price,
                    count=count,
                    costs=costs,
                    share=share,
                    dividend=dividend,
                    owner=user
                ))
            else:
                print("Введите необходимые данные на странице дивидендные акции")
                break

        AssetCandidates.objects.filter(owner=user).all().delete()
        AssetCandidates.objects.bulk_create(assets_to_add)
