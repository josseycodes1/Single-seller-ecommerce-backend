from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, NewsletterSubscription, Banner

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")
    search_fields = ("name",)
    ordering = ("name",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 4  


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "price", "stock", "is_featured", "category", "created_at")
    list_filter = ("is_featured", "category")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    inlines = [ProductImageInline] 


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ("id", "customer_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "customer_email")
    ordering = ("-created_at",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "price", "order")
    list_filter = ("product",)


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at")
    search_fields = ("email",)
    ordering = ("-subscribed_at",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "link")
    search_fields = ("title",)
