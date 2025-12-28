from django.core.cache import cache
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Онуление счетчиков"

    def handle(self, *args, **options):
        counter = cache.get('API_REQUESTS_COUNTER')
        self.stdout.write(self.style.WARNING(f"Значение счетчика: {counter}"))
        if counter:
            cache.set('API_REQUESTS_COUNTER', 0)
            self.stdout.write(self.style.WARNING("Счетчик сброшен"))
