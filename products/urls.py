from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
        CategoryViewSet, 
        ProductViewSet, 
        OrderViewSet, 
        NewsletterSubscriptionViewSet, 
        BannerViewSet, 
        SellerRegisterView,
        CustomTokenObtainPairView,  
        password_reset_request, 
        password_reset_confirm,
        CartAPIView, 
        CartItemAPIView, 
        ClearCartAPIView,
        password_resend_code
       
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'newsletter', NewsletterSubscriptionViewSet)
router.register(r'banners', BannerViewSet)

urlpatterns = [
    path("", include(router.urls)), 
    path("register/seller/", SellerRegisterView.as_view(), name="seller-register"),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/password-reset/request/", password_reset_request, name="password-reset-request"),
    path("auth/password-reset/confirm/", password_reset_confirm, name="password-reset-confirm"),
    path("auth/password-reset/resend/", password_resend_code, name="password-resend-code"),
    path("cart/", CartAPIView.as_view(), name="cart-create"),
    path("cart/items/", CartItemAPIView.as_view(), name="cart-add-item"),
    path("cart/items/<int:item_id>/", CartItemAPIView.as_view(), name="cart-update-item"),
    path("cart/clear/", ClearCartAPIView.as_view(), name="cart-clear"),
]

# frontend can now fetch:
# /api/products/ → All products
# /api/categories/ → All categories
# /api/orders/ → Orders (brand side)
# /api/banners/ → Homepage banners
# /api/newsletter/ → Newsletter subscribers

#test in Postman
#list all products: GET http://127.0.0.1:8000/api/products/
#get single product: GET http://127.0.0.1:8000/api/products/1/
#add new product: POST http://127.0.0.1:8000/api/products/ (send JSON body + image if needed)
#update product: PUT http://127.0.0.1:8000/api/products/1/
#delete product: DELETE http://127.0.0.1:8000/api/products/1/