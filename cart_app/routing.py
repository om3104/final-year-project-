from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/cart/(?P<cart_id>\d+)/$', consumers.ProductScanConsumer.as_asgi()),
] 