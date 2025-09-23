from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, NewsletterSubscription, Banner
from .models import Banner, Cart, CartItem 

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
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_total_price', 'added_at')
    fields = ('product', 'quantity', 'get_total_price', 'added_at')
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price.short_description = 'Total Price'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_total_quantity', 'get_total_price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('id',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'get_total_price_display', 'get_total_quantity_display')
    inlines = [CartItemInline]
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
        ('Cart Summary', {
            'fields': ('get_total_quantity_display', 'get_total_price_display'),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_quantity(self, obj):
        return obj.get_total_quantity()
    get_total_quantity.short_description = 'Total Items'
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price.short_description = 'Total Value'
    
    def get_total_price_display(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price_display.short_description = 'Total Cart Value'
    
    def get_total_quantity_display(self, obj):
        return obj.get_total_quantity()
    get_total_quantity_display.short_description = 'Total Items in Cart'

    def has_add_permission(self, request):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'get_total_price', 'added_at')
    list_filter = ('added_at', 'cart', 'product')
    search_fields = ('cart__id', 'product__name')
    readonly_fields = ('added_at', 'get_total_price_display')
    list_select_related = ('cart', 'product')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('cart', 'product', 'quantity')
        }),
        ('Price Information', {
            'fields': ('get_total_price_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_price(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price.short_description = 'Total Price'
    
    def get_total_price_display(self, obj):
        return f"${obj.get_total_price():.2f}"
    get_total_price_display.short_description = 'Total Price'
    
    def has_add_permission(self, request):
        return False


admin.site.site_header = "E-commerce Admin"
admin.site.site_title = "E-commerce Administration"
admin.site.index_title = "Welcome to E-commerce Admin"