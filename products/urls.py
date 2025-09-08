from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, OrderViewSet, NewsletterSubscriptionViewSet, BannerViewSet, SellerRegisterView
from django.urls import path, include
from .views import CustomTokenObtainPairView,  user_profile
from rest_framework_simplejwt.views import TokenRefreshView

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
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
     path("api/user/profile/", user_profile, name="user-profile"), 
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