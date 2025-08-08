from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, OrderViewSet, NewsletterSubscriptionViewSet, BannerViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'newsletter', NewsletterSubscriptionViewSet)
router.register(r'banners', BannerViewSet)

urlpatterns = router.urls

# frontend can now fetch:
# /api/products/ → All products
# /api/categories/ → All categories
# /api/orders/ → Orders (brand side)
# /api/banners/ → Homepage banners
# /api/newsletter/ → Newsletter subscribers

# Test in Postman
# List all products: GET http://127.0.0.1:8000/api/products/
# Get single product: GET http://127.0.0.1:8000/api/products/1/
# Add new product: POST http://127.0.0.1:8000/api/products/ (send JSON body + image if needed)
# Update product: PUT http://127.0.0.1:8000/api/products/1/
# Delete product: DELETE http://127.0.0.1:8000/api/products/1/