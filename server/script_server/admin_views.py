from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
import json
from .models import UserSettings

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_user_settings(request, user_id):
    try:
        settings = UserSettings.objects.get(user_id=user_id)
        return JsonResponse({
            'success': True,
            'settings': {
                'user_id': settings.user_id,
                'settings': settings.settings
            }
        })
    except ObjectDoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User settings not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@user_passes_test(is_admin)
@require_http_methods(["PUT"])
def update_user_settings(request, user_id):
    try:
        data = json.loads(request.body)
        settings_obj, created = UserSettings.objects.get_or_create(user_id=user_id)
        settings_obj.settings = data.get('settings', {})
        settings_obj.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Settings updated successfully',
            'settings': {
                'user_id': settings_obj.user_id,
                'settings': settings_obj.settings
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
