# products/urls.py
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, OrderViewSet, NewsletterSubscriptionViewSet, BannerViewSet, SellerRegisterView
from django.urls import path, include
from .views import CustomTokenObtainPairView, user_profile
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'newsletter', NewsletterSubscriptionViewSet)
router.register(r'banners', BannerViewSet)

urlpatterns = [
  
    path("register/seller/", SellerRegisterView.as_view(), name="seller-register"),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/user/profile/", user_profile, name="user-profile"),
    
  
    path("", include(router.urls)), 
]