from django import forms

from strategy.models import Settings, CheckAssets


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = [
            'available_capital',
            'broker_commission',
            'dividend_tax',
            'central_bank_rate',
            'dividends_from_date',
            'dividends_to_date',
            'tg_id'
        ]

class CheckAssetsForm(forms.ModelForm):
    class Meta:
        model = CheckAssets
        fields = ['ticker', 'buy_price', 'buy_count', 'buy_date', 'current_price', 'excepted_price', 'owner']
