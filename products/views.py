from django.shortcuts import render
from rest_framework import viewsets
from .models import Category, Product, Order, NewsletterSubscription, Banner
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    NewsletterSerializer,
    BannerSerializer,
    SellerRegisterSerializer
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
from .models import NewsletterSubscription

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

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSerializer

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
        
        # Check if email already exists
        if NewsletterSubscription.objects.filter(email=email).exists():
            return Response({"message": "Email already subscribed"}, status=status.HTTP_200_OK)
        
        # Create new subscription
        subscription = NewsletterSubscription(email=email)
        subscription.save()
        
        return Response({"message": "Subscribed successfully"}, status=status.HTTP_201_CREATED)