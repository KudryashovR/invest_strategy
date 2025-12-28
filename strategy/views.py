import json
import subprocess

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import SettingsForm, CheckAssetsForm
from .models import CheckAssets, AssetData, Settings, AssetDividend, AssetCandidates


@login_required
def dashboard(request):
    user = get_user_model().objects.filter(username=request.user).first()
    assets = CheckAssets.objects.filter(owner=user.pk).all()
    data = {}
    total_price = 0
    total_p_f = 0
    total_owner_period = 0

    for asset in assets:
        asset_data = AssetData.objects.filter(ticker=asset.ticker).first()
        last_price = asset_data.get_price()
        asset.set_current_price(last_price)
        total_price += last_price * asset.buy_count
        holding_time = asset.get_holding_time()
        total_owner_period = max(total_owner_period, holding_time)
        price_diff = asset.get_price_diff()
        total_p_f += price_diff
        expected_price_by_key_rate = asset.get_expected_price_by_key_rate()
        is_can_sold = asset.get_is_can_sold()
        is_danger = asset.get_is_danger()
        logo_url = asset_data.logo_url
        data[f'{asset.ticker}_{asset.pk}'] = (
            logo_url, #0
            asset.buy_price, #1
            asset.buy_count, #2
            asset.buy_date, #3
            holding_time, #4
            asset.current_price, #5
            price_diff, #6
            expected_price_by_key_rate, #7
            is_can_sold, #8
            asset.excepted_price, #9
            is_danger, #10
            asset.pk #11
        )

    total_assets = len(assets)

    context = {
        'assets': data,
        'total_assets': total_assets,
        'total_price': total_price,
        'total_p_f': total_p_f,
        'total_owner_period': total_owner_period
    }

    return render(request, 'strategy/dashboard.html', context)


@login_required
@require_POST
@csrf_exempt  # или используйте @ensure_csrf_cookie
def update_item(request, item_id):
    try:
        data = json.loads(request.body)

        field = data.get('field').split(':')[1]
        value = data.get('value').replace(',', '.')
        base = data.get('field').split(':')[0]

        match(base):
            case 'check_asset':
                asset = CheckAssets.objects.get(id=item_id)
            case 'asset_dividend':
                asset = AssetDividend.objects.get(id=item_id)
            case _:
                return JsonResponse({'success': False, 'error': f'База {base} не найдена'})

        # Валидация
        if not field or value is None:
            return JsonResponse({'success': False, 'error': 'Не указано поле или значение'})

        # Преобразуем значение в нужный тип
        try:
            if field in ['buy_price', 'excepted_price']:
                value = float(value)
            elif field in ['buy_count', 'priority', 'max_part']:
                value = int(value)
            elif field in ['buy_date']:
                parts = value.split('.')
                value = f'{parts[2]}-{parts[1]}-{parts[0]}'
            else:
                return JsonResponse({'success': False, 'error': f'Поле {field} отсутствует в базе {base}'})
        except ValueError as err:
            return JsonResponse({'success': False, 'error': f'Некорректное числовое значение: {err}'})

        # Обновляем поле
        if hasattr(asset, field):
            if base == 'asset_dividend':
                match value:
                    case 1:
                        max_part = 1
                    case 3:
                        max_part = 10
                    case 5:
                        max_part = 20
                    case _:
                        return JsonResponse({'success': False, 'error': "Доступные значения приоритета: 1, 3 и 5"})
                setattr(asset, 'max_part', max_part)
                asset.save()

            setattr(asset, field, value)
            asset.save()

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': f'Поле {field} не существует'})

    except CheckAssets.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Объект не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def settings_edit(request):
    user = get_user_model().objects.filter(username=request.user).first()
    settings = Settings.objects.filter(owner=user).first()

    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=settings)

        if form.is_valid():
            device = form.save()

            return redirect('settings')
    else:
        form = SettingsForm(instance=settings)

    context = {'form': form, 'device': settings}

    return render(request, 'strategy/settings.html', context)

@login_required
def devidends(request):
    username = request.user
    user = get_object_or_404(User, username=username)
    date_from = Settings.objects.filter(owner=user).first().dividends_from_date
    date_to = Settings.objects.filter(owner=user).first().dividends_to_date
    assets = AssetDividend.objects.filter(owner=user).all()
    data = {}

    for asset in assets:
        asset_data = AssetData.objects.filter(ticker=asset.ticker).first()
        data[asset.ticker] = (
            asset_data.logo_url, #0
            asset.company_name, #1
            asset.payday, #2
            asset.dividend, #3
            asset.profitability, #4
            asset.price, #5
            asset.priority, #6
            asset.max_part, #7
            asset.pk #8
        )

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'assets': data
    }

    return render(request, 'strategy/dividends.html', context)


@login_required
@require_POST
def update_dividends(request):
    """Выполняет команду обновления дивидендов"""
    try:
        # Запускаем команду обновления дивидендов
        username = request.user
        user_pk = get_object_or_404(User, username=username).pk
        result = subprocess.run(
            ['python3', 'manage.py', 'updates_dividends', '--user-id', str(user_pk)],
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR
        )

        if result.returncode == 0:
            return JsonResponse({
                'status': 'success',
                'message': 'Данные о дивидендах успешно обновлены',
                'refresh': True  # Флаг для перезагрузки страницы
            })
        else:
            print(result.stderr)
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при выполнении команды: {result.stderr}'
            }, status=500)

    except Exception as e:
        print(e)
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка: {str(e)}'
        }, status=500)

@login_required
def asset_add(request):
    if request.method == 'POST':
        form = CheckAssetsForm(request.POST)

        if form.is_valid():
            device = form.save()

            return redirect('dashboard')
    else:
        form = CheckAssetsForm()

    context = {'form': form}

    return render(request, 'strategy/add_asset.html', context)

@login_required
def asset_delete(request, pk):
    asset = get_object_or_404(CheckAssets, pk=pk)

    if request.method == 'POST':
        asset.delete()

        return redirect('dashboard')

    context = {'asset': asset}

    return render(request, 'strategy/delete_asset.html', context)

@login_required
def candidates(request):
    username = request.user
    user = get_object_or_404(User, username=username)
    date_from = Settings.objects.filter(owner=user).first().dividends_from_date
    date_to = Settings.objects.filter(owner=user).first().dividends_to_date
    assets = AssetCandidates.objects.filter(owner=user).all()
    data = {}
    total_count = 0
    total_costs = 0
    total_share = 0
    total_dividend = 0

    for asset in assets:
        if asset.count:
            asset_data = AssetData.objects.filter(ticker=asset.ticker).first()
            data[asset.ticker] = (
                asset_data.logo_url,  # 0
                asset.price,  # 1
                asset.count,  # 2
                asset.costs,  # 3
                asset.share,  # 4
                asset.dividend,  # 5
            )
            total_count += asset.count
            total_costs += asset.costs
            total_share += asset.share
            total_dividend += asset.dividend

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'assets': data,
        'total_count': total_count,
        'total_costs': total_costs,
        'total_share': total_share,
        'total_dividend': total_dividend
    }

    return render(request, 'strategy/candidates.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()

    return render(request, 'strategy/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Аккаунт создан для {user.username}!')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()

    return render(request, 'strategy/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('login')

@login_required
@require_POST
def get_candidates(request):
    try:
        username = request.user
        user_pk = get_object_or_404(User, username=username).pk
        result = subprocess.run(
            ['python3', 'manage.py', 'get_candidates', '--user-id', str(user_pk)],
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR
        )

        if result.returncode == 0:
            return JsonResponse({
                'status': 'success',
                'message': 'Данные о дивидендах успешно обновлены',
                'refresh': True  # Флаг для перезагрузки страницы
            })
        else:
            print(result.stderr)
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при выполнении команды: {result.stderr}'
            }, status=500)

    except Exception as e:
        print(e)
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка: {str(e)}'
        }, status=500)
