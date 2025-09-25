from django.shortcuts import render
from rest_framework import viewsets
from .models import Category, Product, Order, NewsletterSubscription, Banner
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
        """Create a new empty cart and return it."""
        cart = Cart.objects.create()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        """Fetch an existing cart by ?cart_id=12."""
        cart_id = request.query_params.get("cart_id")
        if not cart_id:
            return Response({"detail": "cart_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=int(cart_id)) 
        except (ValueError, Cart.DoesNotExist):
            return Response({"detail": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartSerializer(cart)
        return Response(serializer.data)

class CartItemAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart_id = request.data.get("cart_id")
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)
        color = request.data.get("color", None)

        if not cart_id or not product_id:
            return Response({"detail": "cart_id and product_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=int(cart_id))  # 👈 cast to int
            product = Product.objects.get(id=int(product_id))
        except (ValueError, Cart.DoesNotExist, Product.DoesNotExist):
            return Response({"detail": "Cart or Product not found"}, status=status.HTTP_404_NOT_FOUND)


        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, color=color)
        cart_item.quantity += int(quantity)
        cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, item_id):
      
        serializer = UpdateCartItemSerializer(data=request.data)
        if serializer.is_valid():
            cart_id = request.data.get('cart_id')
            quantity = serializer.validated_data['quantity']

            if not cart_id:
                return Response({"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                cart_item = CartItem.objects.get(id=item_id, cart_id=cart_id)
            except CartItem.DoesNotExist:
                return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

           
            if quantity > cart_item.product.stock:
                return Response(
                    {"error": f"Only {cart_item.product.stock} items available in stock"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = quantity
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
            cart = Cart.objects.get(id=int(cart_id))  # 👈 cast to int
            cart_item = CartItem.objects.get(id=pk, cart=cart)
        except (ValueError, Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response({"detail": "Cart or CartItem not found"}, status=status.HTTP_404_NOT_FOUND)

        cart_item.quantity = int(quantity)
        cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request, pk):
        """Remove a cart item."""
        cart_id = request.data.get("cart_id")
        if not cart_id:
            return Response({"detail": "cart_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(id=int(cart_id))  # 👈 cast to int
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
            cart = Cart.objects.get(id=int(cart_id))  # 👈 cast to int
        except (ValueError, Cart.DoesNotExist):
            return Response({"detail": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)

        cart.items.all().delete()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
