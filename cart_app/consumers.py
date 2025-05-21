import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from decimal import Decimal
from .models import RFIDCard, Product, Cart, CartWeight, CartItem
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)

class ProductScanConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.cart_id = self.scope['url_route']['kwargs'].get('cart_id')
        logger.info(f"[WebSocket] Client attempting to connect for cart {self.cart_id}")
        
        if not self.cart_id:
            # Try to get or create a cart for the user
            user = self.scope.get('user')
            if user and user.is_authenticated:
                cart = await self.get_or_create_cart(user)
                if cart:
                    self.cart_id = cart.id
                    logger.info(f"[WebSocket] Created new cart with ID: {self.cart_id}")
                else:
                    logger.error("[WebSocket] Failed to create cart for user")
                    await self.close()
                    return
            else:
                logger.error("[WebSocket] No authenticated user found")
            await self.close()
            return
            
        await self.accept()
        logger.info(f"[WebSocket] Client connected successfully for cart {self.cart_id}")

    async def disconnect(self, close_code):
        logger.info(f"[WebSocket] Client disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            logger.debug(f"[WebSocket] Received data: {text_data}")
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'rfid':
                await self.handle_rfid(data)
            elif message_type == 'weight':
                await self.handle_weight(data)
            else:
                await self.send(text_data=json.dumps({
                    'error': 'Invalid message type'
                }))
        except json.JSONDecodeError:
            logger.error("[WebSocket] Invalid JSON received")
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON data'
            }))
        except Exception as e:
            logger.error(f"[WebSocket] Error: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': 'Internal server error'
            }))

    async def handle_rfid(self, data):
        card_id = data.get('card_id')
        if not card_id:
            await self.send(text_data=json.dumps({
                'error': 'No card_id provided'
            }))
            return
        
        product_data = await self.get_product_data(card_id)
        
        if product_data:
            logger.info(f"[WebSocket] Found product for card_id: {card_id}")
            
            # Add product to cart
            cart = await self.get_cart()
            if cart:
                await self.add_to_cart(cart, product_data['id'])
                product_data['added_to_cart'] = True
            else:
                product_data['added_to_cart'] = False
                logger.warning(f"[WebSocket] No active cart found for product: {card_id}")
            
            await self.send(text_data=json.dumps({
                'type': 'rfid_success',
                'data': product_data
            }))
        else:
            logger.warning(f"[WebSocket] No product found for card_id: {card_id}")
            await self.send(text_data=json.dumps({
                'type': 'rfid_error',
                'error': 'Product not found'
            }))

    async def handle_weight(self, data):
        try:
            raw_weight = data.get('weight', 0)
            raw_value = data.get('raw', 0)  # Raw sensor value for debugging
            
            # Convert weight to positive decimal
            weight = abs(Decimal(str(raw_weight)))
            
            logger.info(f"[WebSocket] Processing weight: {weight} kg (raw: {raw_value})")
            
            # Calculate expected weight from cart items
            cart = await self.get_cart()
            if cart:
                await self.database_sync_to_async(cart.update_total_weight)()
                expected_weight = cart.total_weight
            else:
                expected_weight = Decimal('0.000')
            
            # Send weight status to all connected clients
            response = {
                'type': 'weight_status',
                'status': 'ok',
                'measured_weight': str(weight),
                'expected_weight': str(expected_weight),
                'difference': str(abs(weight - expected_weight))
            }
            
            await self.send(text_data=json.dumps(response))
            
        except (TypeError, ValueError) as e:
            logger.error(f"[WebSocket] Error processing weight: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'weight_error',
                'error': 'Invalid weight data'
            }))

    @database_sync_to_async
    def get_cart(self):
        try:
            return Cart.objects.get(id=self.cart_id, is_active=True)
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def get_product_data(self, card_id):
        try:
            rfid_card = RFIDCard.objects.get(card_id=card_id)
            product = Product.objects.get(rfid_card=rfid_card)
            return {
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'weight': str(product.weight),
                'description': product.description,
                'image': product.image.url if product.image else None
            }
        except (RFIDCard.DoesNotExist, Product.DoesNotExist):
            return None

    @database_sync_to_async
    def add_to_cart(self, cart, product_id):
        try:
            product = Product.objects.get(id=product_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 1}
            )
            
            if not created:
                cart_item.quantity += 1
                cart_item.save()
            
            # Update cart total weight
            cart.update_total_weight()
            
            return True
        except Exception as e:
            logger.error(f"[WebSocket] Error adding product to cart: {str(e)}")
            return False

    async def weight_update(self, event):
        # Send weight update to the client
        await self.send(text_data=json.dumps({
            'type': 'weight',
            'weight': event['weight']
        })) 

    @database_sync_to_async
    def get_or_create_cart(self, user):
        try:
            cart, created = Cart.objects.get_or_create(user=user, is_active=True)
            return cart
        except Exception as e:
            logger.error(f"[WebSocket] Error creating cart: {str(e)}")
            return None 