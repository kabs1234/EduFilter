from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import UserStatus
import json

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
