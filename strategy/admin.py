from django.contrib import admin
from .models import CheckAssets, AssetData, Settings, AssetDividend, AssetCandidates


@admin.register(CheckAssets)
class CheckAssetsAdmin(admin.ModelAdmin):
    list_display = [
        'ticker',
        'buy_price',
        'buy_count',
        'buy_date',
        'current_price',
        'excepted_price',
        'is_notified',
        'owner'
    ]
    search_fields = ['ticker']

    class Meta:
        model = CheckAssets
        fields = '__all__'

@admin.register(AssetData)
class AssetDataAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'class_code', 'nano', 'units', 'get_price', 'logo_url']
    search_fields = ['ticker']

    class Meta:
        model = AssetData
        fields = '__all__'

@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = [
        'available_capital',
        'broker_commission',
        'dividend_tax',
        'central_bank_rate',
        'dividends_from_date',
        'dividends_to_date',
        'tg_id'
    ]

    class Meta:
        model = Settings
        fields = '__all__'

@admin.register(AssetDividend)
class AssetDividendAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'company_name', 'payday', 'dividend', 'profitability', 'price', 'priority', 'max_part']

    class Meta:
        model = AssetDividend
        fields = '__all__'

@admin.register(AssetCandidates)
class AssetCandidatesAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'price', 'count', 'costs', 'share', 'dividend']

    class Meta:
        model = AssetCandidates
        fields = '__all__'
