import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from .models import UserSettings
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle new WebSocket connection"""
        # Store client info
        self.client_ip = self.scope['client'][0]
        self.client_port = self.scope['client'][1]
        
        # Accept the connection
        await self.accept()
        
        # Add to the general status group
        await self.channel_layer.group_add("status_updates", self.channel_name)
        
        logger.info(f"WebSocket Connection: Client={self.client_ip}:{self.client_port}, Channel={self.channel_name}")
        logger.debug(f"Connection Headers: {dict(self.scope['headers'])}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Remove from the status group
        await self.channel_layer.group_discard("status_updates", self.channel_name)
        logger.info(f"WebSocket Disconnected: Client={self.client_ip}:{self.client_port}, Code={close_code}")

    async def receive(self, text_data):
        """Handle received messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            logger.info(f"WebSocket Message Received: Type={message_type}, From={self.client_ip}:{self.client_port}")
            logger.debug(f"Message Content: {data}")
            
            if message_type == 'admin_connect':
                # Admin connected, store admin status
                self.is_admin = True
                logger.info(f"Admin Connected: {self.client_ip}:{self.client_port}")
                await self.send(text_data=json.dumps({
                    'type': 'admin_connected',
                    'message': 'Admin connection confirmed'
                }))
                
            elif message_type == 'user_status':
                # Broadcast user status update to admin
                user_id = data.get('user_id')
                status = data.get('status')
                logger.info(f"User Status Update: User={user_id}, Status={status}")
                await self.channel_layer.group_send(
                    "status_updates",
                    {
                        "type": "status_update",
                        "message": {
                            "type": "user_status",
                            "user_id": user_id,
                            "status": status
                        }
                    }
                )
                
            elif message_type == 'settings_change':
                # Broadcast settings change to all connected clients
                user_id = data.get('user_id')
                settings = data.get('settings')
                logger.info(f"Settings Change: User={user_id}")
                logger.debug(f"New Settings: {settings}")
                await self.channel_layer.group_send(
                    "status_updates",
                    {
                        "type": "status_update",
                        "message": {
                            "type": "settings_change",
                            "user_id": user_id,
                            "settings": settings
                        }
                    }
                )
            else:
                logger.warning(f"Unknown message type received: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def status_update(self, event):
        """Handle status updates to be sent to clients"""
        message = event['message']
        logger.info(f"Broadcasting Status Update: Type={message.get('type')}")
        logger.debug(f"Update Content: {message}")
        await self.send(text_data=json.dumps(message))
