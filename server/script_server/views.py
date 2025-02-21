from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import UserStatus, UserIP, UserSettings
import json

@csrf_exempt
def register_ip(request):
    if request.method == 'POST':
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse({'status': 'error', 'message': 'Invalid authorization header'}, status=401)
            
            # Extract token
            token = auth_header.split(' ')[1]
            
            # Parse request body
            data = json.loads(request.body)
            user_id = data.get('user_id')
            ip_address = data.get('ip_address')
            port = data.get('port', 8081)
            
            # Validate token matches user_id
            if not token or token != user_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
            
            # Update or create user IP
            UserIP.objects.update_or_create(
                user_id=user_id,
                defaults={'ip_address': ip_address, 'port': port}
            )
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_user_ips(request):
    user_ips = UserIP.objects.all().values('user_id', 'ip_address', 'port', 'last_updated')
    return JsonResponse({'user_ips': list(user_ips)})

@csrf_exempt
def delete_ip(request):
    if request.method == 'POST':
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse({'status': 'error', 'message': 'Invalid authorization header'}, status=401)
            
            # Extract token
            token = auth_header.split(' ')[1]
            
            # Parse request body
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            # Validate token matches user_id
            if not token or token != user_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
            
            # Delete user IP
            UserIP.objects.filter(user_id=user_id).delete()
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def heartbeat(request):
    if request.method == 'POST':
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse({'status': 'error', 'message': 'Invalid authorization header'}, status=401)
            
            # Extract token
            token = auth_header.split(' ')[1]
            
            # Parse request body
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            # Validate token matches user_id
            if not token or token != user_id:
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
            
            # Update or create user status
            user_status, created = UserStatus.objects.get_or_create(user_id=user_id)
            user_status.update_heartbeat()
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_online_users(request):
    # Mark users as offline if they haven't sent a heartbeat in 10 seconds
    UserStatus.mark_offline_inactive_users(timeout_minutes=0.167)  # 10 seconds = 0.167 minutes
    
    # Get all online users
    online_users = UserStatus.objects.filter(is_online=True).values('user_id', 'last_heartbeat')
    return JsonResponse({'online_users': list(online_users)})

@csrf_exempt
def user_settings(request, user_id):
    if request.method == 'GET':
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid authorization header format. Expected: Bearer <token>'
                }, status=401)
            
            # Extract token and verify it matches the URL user_id
            token = auth_header.split(' ')[1]
            if token != user_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Token does not match user ID'
                }, status=401)
            
            # Get or create user settings
            try:
                settings = UserSettings.get_user_settings(user_id)
                
                response_data = {
                    'status': 'success',
                    'blocked_sites': settings.get_blocked_sites(),
                    'excluded_sites': settings.get_excluded_sites(),
                    'categories': settings.categories
                }
                return JsonResponse(response_data)
                
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error getting settings: {str(e)}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    elif request.method == 'POST':
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid authorization header format. Expected: Bearer <token>'
                }, status=401)
            
            # Extract token and verify it matches the URL user_id
            token = auth_header.split(' ')[1]
            if token != user_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Token does not match user ID'
                }, status=401)
            
            # Parse request body
            try:
                data = json.loads(request.body)
                blocked_sites = data.get('blocked_sites', [])
                excluded_sites = data.get('excluded_sites', [])
                categories = data.get('categories', {})
                
                # Get existing settings or create new
                try:
                    settings = UserSettings.objects.get(user_id=user_id)
                except UserSettings.DoesNotExist:
                    settings = UserSettings(user_id=user_id)
                
                # Update settings
                settings.blocked_sites = blocked_sites
                settings.excluded_sites = excluded_sites
                settings.categories = categories
                settings.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Settings updated successfully'
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON data'
                }, status=400)
                
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error updating settings: {str(e)}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': f'Method {request.method} not allowed'
    }, status=405)
