from django.shortcuts import render
from rest_framework import viewsets
from .models import Category, Product, Order, NewsletterSubscription, Banner, Payment, OrderItem, Address
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    NewsletterSerializer,
    BannerSerializer,
    SellerRegisterSerializer,
    CartSerializer, 
    AddToCartSerializer, 
    UpdateCartItemSerializer
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
        email = serializer.validated_data['email']  # Get the email from validated data
        reset_code = serializer.save()
        
        send_mail(
            'Password Reset Code',
            f'Your password reset code is: {reset_code}. It expires in 15 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [email],  # Use the email variable
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
        
        # Send email with the new code
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

class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_seller

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
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsSeller()]
        return []

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
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

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSerializer
    
    def get_permissions(self):
        # Allow anyone to create subscriptions (POST)
        if self.action in ['create']:
            permission_classes = [AllowAny]
        else:
            # Require authentication for other operations (list, retrieve, update, delete)
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    # Add CSRF exemption for create action
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
                    return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
                
                if cart.items.count() == 0:
                    return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
                
               
                address = Address.objects.create(
                    country=address_data['country'],
                    street_address=address_data['street_address'],
                    town=address_data['town'],
                    state=address_data['state'],
                    postal_code=address_data['postal_code'],
                    is_default=False
                )
                
           
                order = Order.objects.create(
                    customer_name=customer_name,
                    customer_email=email,
                    customer_phone=customer_phone,
                    address=address,
                    order_notes=order_notes,
                    status='pending'
                )
                
              
                total_amount = 0
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                        color=cart_item.color
                    )
                    total_amount += cart_item.quantity * cart_item.product.price
                
                order.total_amount = total_amount
                order.save()
                
                return Response({
                    "success": True,
                    "order_id": order.id,
                    "total_amount": float(total_amount),
                    "message": "Order created successfully"
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Checkout error: {str(e)}")
                return Response({"error": "Failed to create order"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InitializePaymentAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = InitializePaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart = serializer.validated_data['cart']
                email = serializer.validated_data['email']
                callback_url = serializer.validated_data.get('callback_url')
                
                total_amount = cart.get_total_price()
                
                if total_amount <= 0:
                    return Response({"error": "Invalid order amount"}, status=status.HTTP_400_BAD_REQUEST)
                
              
                payment_reference = f"PYMT_{uuid.uuid4().hex[:10].upper()}"
                
              
                paystack_service = PaystackService()
                
               
                if not callback_url:
                    callback_url = f"{settings.FRONTEND_URL}/payment/verify"
                
                paystack_response = paystack_service.initialize_payment(
                    email=email,
                    amount=float(total_amount),
                    reference=payment_reference,
                    callback_url=callback_url
                )
                
                if paystack_response.get('status'):
               
                    payment = Payment.objects.create(
                        order=None,  
                        payment_reference=payment_reference,
                        amount=total_amount,
                        email=email,
                        status='pending'
                    )
                    
                    return Response({
                        "success": True,
                        "authorization_url": paystack_response['data']['authorization_url'],
                        "access_code": paystack_response['data']['access_code'],
                        "reference": payment_reference,
                        "amount": float(total_amount),
                        "email": email,
                        "callback_url": callback_url
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Failed to initialize payment",
                        "details": paystack_response.get('message', 'Unknown error')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Payment initialization error: {str(e)}")
                return Response({"error": "Payment initialization failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                        

                        
                        return Response({
                            "success": True,
                            "status": "success",
                            "message": "Payment verified successfully",
                            "payment_data": {
                                "reference": payment.payment_reference,
                                "amount": float(payment.amount),
                                "email": payment.email,
                                "paid_at": data.get('paid_at')
                            }
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

            payment, created = Payment.objects.get_or_create(
                reference=reference,
                defaults={
                    "amount": amount,
                    "status": "success",
                    "payment_method": data.get("channel"),
                },
            )

            if not created: 
                payment.status = "success"
                payment.payment_method = data.get("channel")
                payment.save()

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
        """
        Verify Paystack webhook signature using secret key.
        """
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")

        computed_signature = hmac.new(
            secret, payload, hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)
    """
    Handles Paystack webhook events.
    """

    def post(self, request, *args, **kwargs):
        payload = request.body

      
        signature = request.headers.get("x-paystack-signature")

        if not signature:
            return JsonResponse({"error": "Missing Paystack signature"}, status=400)

        if not self.verify_signature(payload, signature):
            return JsonResponse({"error": "Invalid signature"}, status=400)

     
        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        event_type = event.get("event")
        data = event.get("data", {})

       
        if event_type == "charge.success":
            reference = data.get("reference")
            amount = data.get("amount", 0) / 100 

            payment, created = Payment.objects.get_or_create(
                reference=reference,
                defaults={
                    "amount": amount,
                    "status": "success",
                    "payment_method": data.get("channel"),
                },
            )

            if not created:  
                payment.status = "success"
                payment.payment_method = data.get("channel")
                payment.save()

            return JsonResponse({"status": "success"}, status=200)

       
        return JsonResponse({"status": "ignored", "event": event_type}, status=200)

    def verify_signature(self, payload, signature):
        """
        Verify Paystack webhook signature using your secret key.
        """
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")

        computed_signature = hmac.new(
            secret, payload, hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)