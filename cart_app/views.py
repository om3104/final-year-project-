from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .models import RFIDCard, Product, Cart, CartItem, Order, OrderItem, CartWeight
from .forms import CustomUserCreationForm, CustomAuthenticationForm
import json
from decimal import Decimal
import logging
import razorpay

logger = logging.getLogger(__name__)

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            print(phone_number, password)
            user = authenticate(username=phone_number, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back!')
                return redirect('home')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

@login_required
def profile_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders
    }
    return render(request, 'auth/profile.html', context)

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'auth/change_password.html', {'form': form})

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('home')
    return redirect('profile')

def product_list_view(request):
    cart = Cart.objects.filter(user=request.user, is_active=True).first() if request.user.is_authenticated else None
    cart_count = CartItem.objects.filter(cart=cart).count() if cart else 0
    
    context = {
        'cart_count': cart_count,
    }
    return render(request, 'cart_app/product_list.html', context)

@login_required
def cart_view(request):
    # Get or create cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)
    cart_items = CartItem.objects.filter(cart=cart)
    
    cart_total = sum(item.product.price * item.quantity for item in cart_items)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart_total
    }
    return render(request, 'cart_app/cart.html', context)

@login_required
@csrf_exempt
def update_quantity(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            action = data.get('action')
            value = data.get('value')
            
            cart = Cart.objects.get(user=request.user, is_active=True)
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            
            if action == 'increase':
                cart_item.quantity += 1
                cart_item.save()
            elif action == 'decrease':
                cart_item.quantity = max(0, cart_item.quantity - 1)
                if cart_item.quantity == 0:
                    cart_item.delete()
                else:
                    cart_item.save()
            elif action == 'set':
                cart_item.quantity = max(0, int(value))
                if cart_item.quantity == 0:
                    cart_item.delete()
                else:
                    cart_item.save()
            elif action == 'remove':
                cart_item.delete()
            
            # Update cart total weight after any change
            cart.update_total_weight()
            
            return JsonResponse({
                'success': True,
                'message': 'Cart updated successfully'
            })
            
        except CartItem.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)
        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            if not product_id:
                return JsonResponse({'error': 'Product ID is required'}, status=400)
            
            product = Product.objects.get(id=product_id)
            cart, created = Cart.objects.get_or_create(user=request.user, is_active=True)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity = quantity
                cart_item.save()
            
            # Update cart total weight
            cart.update_total_weight()
            
            # Get updated cart count
            cart_count = CartItem.objects.filter(cart=cart).count()
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'message': 'Product added to cart successfully'
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        except Exception as e:
            logger.error(f"Error adding to cart: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def checkout_view(request):
    cart = Cart.objects.filter(user=request.user, is_active=True).first()
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty')
        return redirect('cart')
    
    cart_items = cart.items.all()
    cart_total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Razorpay integration
    client = razorpay.Client(auth=("rzp_test_Y4uz4jerKyjRHZ", "kFYFLo62P9F82ts2DnbB4KJc"))
    
    # Create Razorpay order
    payment = client.order.create({
        "amount": int(cart_total * 100),  # Amount in paise
        "currency": "INR",
        "receipt": f"order_{cart.id}",
        "notes": {
            "user_id": request.user.id,
            "cart_id": cart.id
        }
    })
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'razorpay_order_id': payment['id'],
        'razorpay_key': "rzp_test_Y4uz4jerKyjRHZ",
        'user': request.user
    }
    return render(request, 'cart_app/checkout.html', context)

@login_required
@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')
            
            # Verify payment signature
            client = razorpay.Client(auth=("rzp_test_Y4uz4jerKyjRHZ", "kFYFLo62P9F82ts2DnbB4KJc"))
            
            params_dict = {
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature
            }
            
            client.utility.verify_payment_signature(params_dict)
            
            # Create order from cart
            cart = Cart.objects.get(user=request.user, is_active=True)
            order = Order.objects.create(user=request.user)
            total = Decimal('0.00')
            
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                total += cart_item.product.price * cart_item.quantity
            
            order.total = total
            order.save()
            
            # Clear the cart
            cart.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment successful!',
                'order_id': order.id
            })
            
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'cart_app/order_confirmation.html', {'order': order})

@csrf_exempt
def scan_product(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            card_id = data.get('card_id')
            
            if not card_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Card ID is required'
                }, status=400)

            rfid_card = RFIDCard.objects.get(card_id=card_id)
            product = Product.objects.get(rfid_card=rfid_card)
            
            response_data = {
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': str(product.price),
                    'description': product.description,
                    'image': product.image.url if product.image else None
                }
            }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except RFIDCard.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'RFID card not found: {card_id}'
            }, status=404)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No product associated with this RFID card'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Only POST method is allowed'
    }, status=405)

def get_product_details(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'price': float(product.price),
            'weight': float(product.weight)
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

@login_required
def check_cart_item(request, product_id):
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
        return JsonResponse({
            'quantity': cart_item.quantity
        })
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        return JsonResponse({
            'quantity': 0
        })

@csrf_exempt
def check_weight(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 0))
            expected_weight = Decimal(str(data.get('expected_weight', 0)))
            
            # Get the latest weight from the load cell
            try:
                latest_weight = CartWeight.objects.filter(
                    cart__user=request.user,
                    cart__is_active=True
                ).latest('timestamp').actual_weight
            except CartWeight.DoesNotExist:
                return JsonResponse({
                    'error': 'No weight data available'
                }, status=400)
            
            # Allow for a small margin of error (e.g., 50g)
            margin_of_error = Decimal('0.050')
            weight_discrepancy = abs(latest_weight - expected_weight) > margin_of_error
            
            return JsonResponse({
                'weight_discrepancy': weight_discrepancy,
                'expected_weight': float(expected_weight),
                'actual_weight': float(latest_weight)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'error': 'Only POST method is allowed'
    }, status=405)

@csrf_exempt
def get_cart_weight(request):
    if request.method == 'GET':
        try:
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
            if not cart:
                return JsonResponse({
                    'error': 'No active cart found'
                }, status=404)
            
            # Get the latest weight record
            latest_weight = CartWeight.objects.filter(cart=cart).latest('timestamp')
            
            return JsonResponse({
                'success': True,
                'measured_weight': float(latest_weight.actual_weight),
                'expected_weight': float(cart.total_weight),
                'difference': float(abs(latest_weight.actual_weight - cart.total_weight))
            })
        except CartWeight.DoesNotExist:
            return JsonResponse({
                'success': True,
                'measured_weight': 0.0,
                'expected_weight': float(cart.total_weight),
                'difference': float(cart.total_weight)
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'error': 'Only GET method is allowed'
    }, status=405)