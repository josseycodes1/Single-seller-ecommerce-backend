from django.shortcuts import render
from rest_framework import viewsets
from .models import Category, Product, Order, NewsletterSubscription, Banner, Payment, OrderItem, Address, ContactMessage
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    NewsletterSerializer,
    BannerSerializer,
    SellerRegisterSerializer,
    CartSerializer, 
    AddToCartSerializer, 
    UpdateCartItemSerializer,
    ContactMessageSerializer
)
from rest_framework.permissions import BasePermission
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from django.core.mail import send_mail
from django.conf import settings
from .serializers import PasswordResendCodeSerializer
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import NewsletterSubscription, Cart, CartItem
import logging
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets, status, filters
import uuid
from .paystack import PaystackService
from .serializers import PaymentSerializer, InitializePaymentSerializer, VerifyPaymentSerializer, CheckoutSerializer
import json
import hmac
import hashlib
from django.conf import settings
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email'] 
        reset_code = serializer.save()
        
        send_mail(
            'Password Reset Code',
            f'Your password reset code is: {reset_code}. It expires in 15 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [email], 
            fail_silently=False,
        )

        return Response({
            "message": "Password reset code sent to email"
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Password reset successfully"
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_resend_code(request):
    serializer = PasswordResendCodeSerializer(data=request.data)
    
    if serializer.is_valid():
        reset_code, email = serializer.save()
        
      
        send_mail(
            'Password Reset Code',
            f'Your new password reset code is: {reset_code}. It expires in 15 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        return Response({
            "message": "New password reset code sent to email"
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

User = get_user_model()
class SellerRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SellerRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Seller registered successfully!"},
            status=status.HTTP_201_CREATED
        )

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]  
    ordering_fields = ["price", "created_at"] 
    
 
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
         
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        print(f"DEBUG: Create method - User: {request.user}")
        print(f"DEBUG: User is authenticated: {request.user.is_authenticated}")
        if request.user.is_authenticated:
            print(f"DEBUG: User is seller: {request.user.is_authenticated}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.error(f"Validation failed: {e.detail}")
            return Response({"errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error while creating product")
            return Response(
                {"error": "Something went wrong. Check server logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
    def get_queryset(self):
        queryset = Product.objects.all()
        
   
        is_featured = self.request.query_params.get('is_featured')
        if is_featured is not None:
            if is_featured.lower() == 'true':
                queryset = queryset.filter(is_featured=True)
            elif is_featured.lower() == 'false':
                queryset = queryset.filter(is_featured=False)
        
       
        limit = self.request.query_params.get('limit')
        if limit is not None:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass 
        
        return queryset
    
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSerializer
    
    def get_permissions(self):

        if self.action in ['create']:
            permission_classes = [AllowAny]
        else:
           
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
   
    @method_decorator(csrf_exempt, name='dispatch')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Banner.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = BannerSerializer
    permission_classes = [permissions.AllowAny] 
    
@method_decorator(csrf_exempt, name='dispatch')
class NewsletterSubscribeView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        if '@' not in email:
            return Response({"error": "Please enter a valid email address"}, status=status.HTTP_400_BAD_REQUEST)
        
   
        if NewsletterSubscription.objects.filter(email=email).exists():
            return Response({"message": "Email already subscribed"}, status=status.HTTP_200_OK)
        
      
        serializer = NewsletterSerializer(data={'email': email})
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Subscribed successfully"}, status=status.HTTP_201_CREATED)
        else:
           
            error_message = list(serializer.errors.values())[0][0] if serializer.errors else "Invalid email"
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        
class CartAPIView(APIView):
    permission_classes = [AllowAny]

    def get_cart(self, cart_id):
        try:
            return Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return None

    def post(self, request):
        cart = Cart.objects.create()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        cart_id = request.query_params.get("cart_id")
        if not cart_id:
            return Response({"detail": "cart_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=cart_id)
        except (ValueError, Cart.DoesNotExist):
            return Response({"detail": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartSerializer(cart)
        return Response(serializer.data)

class CartItemAPIView(APIView):
    permission_classes = [AllowAny]

class CartItemAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = {
            "cart_id": request.data.get("cart_id"),
            "product_id": request.data.get("product_id"),
            "quantity": request.data.get("quantity", 1),
            "color": request.data.get("color")
        }

        cart_id = data["cart_id"]
        if not cart_id:
            return Response({"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AddToCartSerializer(data=data)
        if serializer.is_valid():
            product = serializer.validated_data["product"]
            quantity = serializer.validated_data["quantity"]
            color = serializer.validated_data["color"]

           
            cart = Cart(id=cart_id)
            
          
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, 
                product=product, 
                color=color,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            
            full_cart = Cart.objects.get(id=cart_id)
            cart_serializer = CartSerializer(full_cart)
            return Response(cart_serializer.data, status=status.HTTP_200_OK)

        errors = serializer.errors
        logger.error(f"AddToCart validation failed: {errors}")
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        if serializer.is_valid():
            cart_id = request.data.get('cart_id')
            quantity = serializer.validated_data['quantity']
            color = serializer.validated_data.get('color') 

            if not cart_id:
                return Response({"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                cart_item = CartItem.objects.get(id=item_id, cart_id=cart_id)
            except CartItem.DoesNotExist:
                return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

            
            serializer = UpdateCartItemSerializer(
                data=request.data, 
                context={'cart_item': cart_item} 
            )
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

           
            cart_item.quantity = quantity
            if color: 
                cart_item.color = color
            cart_item.save()

            cart_serializer = CartSerializer(cart_item.cart)
            return Response(cart_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, item_id):
       
        cart_id = request.data.get('cart_id') or request.query_params.get('cart_id')
        
        if not cart_id:
            return Response({"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart_item = CartItem.objects.get(id=item_id, cart_id=cart_id)
            cart = cart_item.cart
            cart_item.delete()
            
            cart_serializer = CartSerializer(cart)
            return Response(cart_serializer.data)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
         
class CartItemDetailView(APIView):
    def put(self, request, pk):
        cart_id = request.data.get("cart_id")
        quantity = request.data.get("quantity")

        if not cart_id or quantity is None:
            return Response({"detail": "cart_id and quantity required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=cart_id)
            cart_item = CartItem.objects.get(id=pk, cart=cart)
        except (ValueError, Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response({"detail": "Cart or CartItem not found"}, status=status.HTTP_404_NOT_FOUND)

        cart_item.quantity = int(quantity)
        cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request, pk):
        cart_id = request.data.get("cart_id")
        if not cart_id:
            return Response({"detail": "cart_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=cart_id)
            cart_item = CartItem.objects.get(id=pk, cart=cart)
        except (ValueError, Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response({"detail": "Cart or CartItem not found"}, status=status.HTTP_404_NOT_FOUND)

        cart_item.delete()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

class ClearCartAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart_id = request.data.get("cart_id")
        if not cart_id:
            return Response({"detail": "cart_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=cart_id)
        except (ValueError, Cart.DoesNotExist):
            return Response({"detail": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        cart.items.all().delete()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CheckoutAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_id = serializer.validated_data['cart_id']
                email = serializer.validated_data['email']
                customer_name = serializer.validated_data['customer_name']
                customer_phone = serializer.validated_data['customer_phone']
                address_data = serializer.validated_data['address']
                order_notes = serializer.validated_data.get('order_notes', '')
                
                try:
                    cart = Cart.objects.get(id=cart_id)
                except Cart.DoesNotExist:
                    return Response({
                        "error": "Cart not found",
                        "details": f"Cart with ID {cart_id} does not exist"
                    }, status=status.HTTP_404_NOT_FOUND)
                
                if cart.items.count() == 0:
                    return Response({
                        "error": "Cart is empty",
                        "details": "Cannot checkout with an empty cart"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    address = Address.objects.create(
                        country=address_data['country'],
                        street_address=address_data['street_address'],
                        town=address_data['town'],
                        state=address_data['state'],
                        postal_code=address_data['postal_code'],
                        is_default=False
                    )
                except Exception as e:
                    return Response({
                        "error": "Failed to create address",
                        "details": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    order = Order.objects.create(
                        customer_name=customer_name,
                        customer_email=email,
                        customer_phone=customer_phone,
                        address=address,
                        order_notes=order_notes,
                        status='pending'
                    )
                except Exception as e:
                    return Response({
                        "error": "Failed to create order",
                        "details": str(e),
                        "field_errors": "Check customer_phone format or other field constraints"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Calculate totals with tax
                TAX_RATE = 0.02
                subtotal = 0
                try:
                    for cart_item in cart.items.all():
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            price=cart_item.product.price,
                            color=cart_item.color
                        )
                        subtotal += cart_item.quantity * cart_item.product.price
                except Exception as e:
                    return Response({
                        "error": "Failed to create order items",
                        "details": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                tax_amount = subtotal * TAX_RATE
                total_amount = subtotal + tax_amount
                
                order.total_amount = total_amount
                order.save()
                
                return Response({
                    "success": True,
                    "order_id": order.id,
                    "subtotal": float(subtotal),
                    "tax_amount": float(tax_amount),
                    "total_amount": float(total_amount),
                    "message": "Order created successfully"
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Checkout error: {str(e)}")
                return Response({
                    "error": "Checkout process failed",
                    "details": str(e),
                    "type": type(e).__name__
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "error": "Invalid data",
            "details": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class InitializePaymentAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        print("DEBUG: InitializePaymentAPIView called")
        print(f"DEBUG: Request data: {request.data}")
        
        serializer = InitializePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"DEBUG: Serializer validation failed: {serializer.errors}")
            return Response({
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print("DEBUG: Serializer is valid")
        
        try:
            cart = serializer.validated_data['cart']
            order = serializer.validated_data['order']  
            email = serializer.validated_data['email']
            callback_url = serializer.validated_data.get('callback_url')
            
            print(f"DEBUG: Cart ID: {cart.id}, Order ID: {order.id}, Email: {email}")
            
            # Calculate total with tax (2%)
            TAX_RATE = 0.02
            subtotal = float(cart.get_total_price())
            tax_amount = subtotal * TAX_RATE
            total_amount = subtotal + tax_amount
            
            print(f"DEBUG: Subtotal: {subtotal}, Tax: {tax_amount}, Total: {total_amount}")
            
            if total_amount <= 0:
                print(f"DEBUG: Invalid amount: {total_amount}")
                return Response({
                    "error": "Invalid order amount",
                    "details": f"Amount must be greater than 0, got {total_amount}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payment_reference = f"PYMT_{uuid.uuid4().hex[:10].upper()}"
            print(f"DEBUG: Payment reference: {payment_reference}")
            
            print("DEBUG: Creating PaystackService instance...")
            paystack_service = PaystackService()
            print("DEBUG: PaystackService instance created")
            
            if not callback_url:
                callback_url = f"{settings.FRONTEND_URL}/payment/verify"
                print(f"DEBUG: Using callback URL: {callback_url}")
            
            # FIX: Convert to kobo correctly
            amount_in_kobo = int(round(total_amount * 100))  # Use int() and round() for safety
            print(f"DEBUG: Amount in kobo: {amount_in_kobo}")
            
            # Verify the amount is reasonable
            if amount_in_kobo > 1000000000:  # 10 million naira safety limit
                print(f"DEBUG: Amount too large: {amount_in_kobo}")
                return Response({
                    "error": "Amount too large",
                    "details": "Payment amount exceeds maximum limit"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order_items = []
            for item in cart.items.all():
                order_items.append(f"{item.product.name} (x{item.quantity}) - ₦{item.product.price}")
            
            metadata = {
                "order_id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": str(order.customer_phone), 
                "items_count": cart.items.count(),
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "custom_fields": [
                    {
                        "display_name": "Order Items",
                        "variable_name": "order_items", 
                        "value": "; ".join(order_items)
                    },
                    {
                        "display_name": "Shipping Address",
                        "variable_name": "shipping_address",
                        "value": f"{order.address.street_address}, {order.address.town}, {order.address.state}"
                    },
                    {
                        "display_name": "Customer Phone",  
                        "variable_name": "customer_phone",
                        "value": str(order.customer_phone) 
                    },
                    {
                        "display_name": "Order Notes", 
                        "variable_name": "order_notes",
                        "value": order.order_notes or "No special instructions"
                    }
                ]
            }
            
            print("DEBUG: Calling Paystack initialize_payment...")
            paystack_response = paystack_service.initialize_payment(
                email=email,
                amount=amount_in_kobo,  # Correct amount in kobo
                reference=payment_reference,
                callback_url=callback_url,
                metadata=metadata 
            )
            
            print(f"DEBUG: Paystack response received: {paystack_response}")
            
            if paystack_response.get('status'):
                print("DEBUG: Creating payment record...")
                payment = Payment.objects.create(
                    order=order,  
                    payment_reference=payment_reference,
                    amount=total_amount,  # Store the total amount with tax
                    email=email,
                    status='pending'
                )
                print(f"DEBUG: Payment record created with ID: {payment.id}")
                
                return Response({
                    "success": True,
                    "authorization_url": paystack_response['data']['authorization_url'],
                    "access_code": paystack_response['data']['access_code'],
                    "reference": payment_reference,
                    "amount": float(total_amount),  # Return the total amount
                    "email": email,
                    "callback_url": callback_url
                }, status=status.HTTP_200_OK)
            else:
                print(f"DEBUG: Paystack failed: {paystack_response}")
                return Response({
                    "error": "Failed to initialize payment with Paystack",
                    "details": paystack_response.get('message', 'Unknown Paystack error'),
                    "paystack_response": paystack_response
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"DEBUG: EXCEPTION CAUGHT: {str(e)}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            logger.error(f"Payment initialization error: {str(e)}", exc_info=True)
            return Response({
                "error": "Payment initialization failed",
                "details": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        reference = request.GET.get('reference')
        
        if not reference:
            return Response({"error": "Reference is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            paystack_service = PaystackService()
            verification_response = paystack_service.verify_payment(reference)
            
            if verification_response.get('status'):
                data = verification_response['data']
                
                try:
                    payment = Payment.objects.get(payment_reference=reference)
                    
                    if data['status'] == 'success':
                        payment.status = 'success'
                        payment.paystack_reference = data.get('reference')
                        payment.save()
                        
                       
                        if payment.order:
                            payment.order.is_paid = True
                            payment.order.payment_status = 'success'
                            payment.order.save()
                        
                        return Response({
                            "success": True,
                            "status": "success",
                            "message": "Payment verified successfully",
                            "payment_data": {
                                "reference": payment.payment_reference,
                                "amount": float(payment.amount),
                                "email": payment.email,
                                "paid_at": data.get('paid_at')
                            },
                            "order_id": payment.order.id if payment.order else None
                        })
                    else:
                        payment.status = 'failed'
                        payment.save()
                        
                        return Response({
                            "success": False,
                            "status": "failed",
                            "message": data.get('gateway_response', 'Payment failed')
                        })
                        
                except Payment.DoesNotExist:
                    return Response({"error": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    "error": "Payment verification failed",
                    "details": verification_response.get('message', 'Unknown error')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response({"error": "Payment verification failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentWebhookAPIView(View):
    def post(self, request, *args, **kwargs):
      
        payload = request.body

      
        try:
            logger.info("Paystack webhook payload: %s", payload.decode("utf-8"))
        except Exception:
            logger.error("Unable to decode Paystack payload")

   
        signature = request.headers.get("x-paystack-signature")
        if not signature:
            logger.warning("Webhook rejected: Missing Paystack signature")
            return JsonResponse({"error": "Missing Paystack signature"}, status=400)


        if not self.verify_signature(payload, signature):
            logger.warning("Webhook rejected: Invalid Paystack signature")
            return JsonResponse({"error": "Invalid signature"}, status=400)


        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Webhook rejected: Invalid JSON format")
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        event_type = event.get("event")
        data = event.get("data", {})

        logger.info("Webhook event received: %s", event_type)

       
        if event_type == "charge.success":
            reference = data.get("reference")
            amount = data.get("amount", 0) / 100 

            try:
                payment = Payment.objects.get(payment_reference=reference)
                payment.status = "success"
                payment.paystack_reference = data.get("reference")
                payment.payment_method = data.get("channel")
                payment.save()
                
              
                if payment.order:
                    payment.order.is_paid = True
                    payment.order.payment_status = 'success'
                    payment.order.save()
                    
            except Payment.DoesNotExist:
               
                payment = Payment.objects.create(
                    payment_reference=reference,
                    amount=amount,
                    status="success",
                    payment_method=data.get("channel"),
                    email=data.get('customer', {}).get('email', '')
                )

            logger.info("Payment processed successfully: %s", reference)
            return JsonResponse({
                "status": "success",
                "reference": reference,
                "amount": amount,
                "payment_method": data.get("channel")
            }, status=200)

       
        logger.info("Unhandled Paystack event type: %s", event_type)
        return JsonResponse({
            "status": "ignored",
            "event": event_type
        }, status=200)

    def verify_signature(self, payload, signature):
       
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")

        computed_signature = hmac.new(
            secret, payload, hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)

class OrderListAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    def get(self, request):
        email = request.GET.get('email')
        
        if not email:
            return Response({"error": "Email parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
          
            orders = Order.objects.filter(customer_email=email).order_by('-created_at')
            
          
            orders_data = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'customer_email': order.customer_email,
                    'customer_phone': str(order.customer_phone) if order.customer_phone else '',
                    'status': order.status,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at,
                    'is_paid': order.is_paid,
                    'payment_status': order.payment_status,
                    'order_notes': order.order_notes,
                    'items': []
                }
                
              
                for item in order.items.all():
                    order_data['items'].append({
                        'id': item.id,
                        'product': {
                            'id': item.product.id,
                            'name': item.product.name,
                            'price': float(item.product.price),
                            'images': [
                                {
                                    'image_url': image.image.url if image.image else None
                                } for image in item.product.images.all()
                            ]
                        },
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'color': item.color
                    })
                
               
                if order.address:
                    order_data['address'] = {
                        'street_address': order.address.street_address,
                        'town': order.address.town,
                        'state': order.address.state,
                        'country': order.address.country,
                        'postal_code': order.address.postal_code
                    }
                
                orders_data.append(order_data)
            
            return Response(orders_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            return Response({"error": "Failed to fetch orders"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GuestOrderListAPIView(APIView):
    
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    def get(self, request):
        print("DEBUG: GuestOrderListAPIView called")
        email = request.GET.get('email')
        
        print(f"DEBUG: Email parameter: {email}")
        
        if not email:
            print("DEBUG: No email provided")
            return Response({"error": "Email parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            print(f"DEBUG: Searching for orders with email: {email}")
            orders = Order.objects.filter(customer_email=email).order_by('-created_at')
            print(f"DEBUG: Found {orders.count()} orders")
            
            orders_data = []
            for order in orders:
                order_data = {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'customer_email': order.customer_email,
                    'customer_phone': str(order.customer_phone) if order.customer_phone else '',
                    'status': order.status,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at,
                    'is_paid': order.is_paid,
                    'payment_status': order.payment_status,
                    'order_notes': order.order_notes,
                    'items': []
                }
                
                for item in order.items.all():
                    order_data['items'].append({
                        'id': item.id,
                        'product': {
                            'id': item.product.id,
                            'name': item.product.name,
                            'price': float(item.product.price),
                            'images': [
                                {
                                    'image_url': image.image.url if image.image else None
                                } for image in item.product.images.all()
                            ]
                        },
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'color': item.color
                    })
                
                if order.address:
                    order_data['address'] = {
                        'street_address': order.address.street_address,
                        'town': order.address.town,
                        'state': order.address.state,
                        'country': order.address.country,
                        'postal_code': order.address.postal_code
                    }
                
                orders_data.append(order_data)
            
            print(f"DEBUG: Returning {len(orders_data)} orders")
            return Response(orders_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"DEBUG: Error fetching guest orders: {str(e)}")
            logger.error(f"Error fetching guest orders: {str(e)}", exc_info=True)
            return Response({"error": "Failed to fetch orders"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class RecentProductsAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 6))
            products = Product.objects.all().order_by('-updated_at')[:limit]
            serializer = ProductSerializer(products, many=True, context={'request': request})
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching recent products: {str(e)}")
            return Response({
                "error": "Failed to fetch recent products"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class ContactMessageAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        logger.info(f"Contact form submission received: {request.data}")
        
        try:
        
            if not request.data:
                return Response({
                    "success": False,
                    "error": {
                        "code": "NO_DATA",
                        "message": "No data provided in request",
                        "details": "Request body is empty"
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
      
            required_fields = ['name', 'email', 'subject', 'message']
            missing_fields = []
            invalid_fields = []
            
            for field in required_fields:
                if field not in request.data:
                    missing_fields.append(field)
                elif not isinstance(request.data[field], str) or not request.data[field].strip():
                    invalid_fields.append({
                        "field": field,
                        "issue": "Field is empty or not a valid string"
                    })
            
            if missing_fields or invalid_fields:
                return Response({
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Form validation failed",
                        "details": {
                            "missing_fields": missing_fields,
                            "invalid_fields": invalid_fields
                        }
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
       
            email = request.data['email']
            if '@' not in email or '.' not in email:
                return Response({
                    "success": False,
                    "error": {
                        "code": "INVALID_EMAIL",
                        "message": "Invalid email format",
                        "details": "Please provide a valid email address"
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
          
            field_limits = {
                'name': 255,
                'email': 254,
                'subject': 255,
                'message': 5000 
            }
            
            length_errors = []
            for field, max_length in field_limits.items():
                if len(request.data[field]) > max_length:
                    length_errors.append({
                        "field": field,
                        "issue": f"Field exceeds maximum length of {max_length} characters",
                        "current_length": len(request.data[field])
                    })
            
            if length_errors:
                return Response({
                    "success": False,
                    "error": {
                        "code": "FIELD_TOO_LONG",
                        "message": "Some fields are too long",
                        "details": {
                            "length_errors": length_errors
                        }
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
      
            serializer = ContactMessageSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    "success": False,
                    "error": {
                        "code": "SERIALIZER_VALIDATION_ERROR",
                        "message": "Data validation failed",
                        "details": serializer.errors
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
          
            try:
                contact_message = serializer.save()
                logger.info(f"Contact message saved successfully - ID: {contact_message.id}")
                
                return Response({
                    "success": True,
                    "message": "Message sent successfully! We'll get back to you soon.",
                    "data": {
                        "id": contact_message.id,
                        "name": contact_message.name,
                        "email": contact_message.email,
                        "subject": contact_message.subject,
                        "status": contact_message.status,
                        "created_at": contact_message.created_at.isoformat()
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as save_error:
                logger.error(f"Database save error: {str(save_error)}", exc_info=True)
                
   
                if "unique" in str(save_error).lower():
                    return Response({
                        "success": False,
                        "error": {
                            "code": "DATABASE_ERROR",
                            "message": "Database constraint violation",
                            "details": "A similar record might already exist"
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        "success": False,
                        "error": {
                            "code": "DATABASE_SAVE_ERROR",
                            "message": "Failed to save message to database",
                            "details": "Please try again later"
                        }
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
        except json.JSONDecodeError:
            return Response({
                "success": False,
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON in request body",
                    "details": "Please check your request format"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as unexpected_error:
            logger.error(f"Unexpected error in contact API: {str(unexpected_error)}", exc_info=True)
            
            return Response({
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": "Please try again later"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)