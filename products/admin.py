from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, NewsletterSubscription, Banner
from .models import Banner, Cart, CartItem, Payment, Address, User

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
    list_display = ("id", "customer_name", "status", "created_at", "total_amount", "is_paid", "payment_status")
    list_filter = ("status", "created_at", "is_paid", "payment_status")
    search_fields = ("customer_name", "customer_email")
    ordering = ("-created_at",)
    readonly_fields = ("total_amount",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "price", "order", "color")
    list_filter = ("product", "color")


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
    fields = ('product', 'quantity', 'color', 'get_total_price', 'added_at')
    
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
    list_display = ('id', 'cart', 'product', 'quantity', 'color', 'get_total_price', 'added_at')
    list_filter = ('added_at', 'cart', 'product', 'color')
    search_fields = ('cart__id', 'product__name')
    readonly_fields = ('added_at', 'get_total_price_display')
    list_select_related = ('cart', 'product')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('cart', 'product', 'quantity', 'color')
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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'order', 'amount', 'status', 'email', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment_reference', 'paystack_reference', 'email', 'order__id')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('order',)
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'payment_reference', 'paystack_reference', 'amount', 'status', 'email')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'country', 'state', 'town', 'street_address', 'is_default')
    list_filter = ('country', 'state', 'is_default')
    search_fields = ('user__email', 'street_address', 'town', 'state', 'postal_code')
    list_select_related = ('user',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'business_name', 'is_seller', 'is_customer', 'is_staff')
    list_filter = ('is_seller', 'is_customer', 'is_staff', 'is_superuser', 'country', 'state')
    search_fields = ('email', 'first_name', 'last_name', 'business_name')
    readonly_fields = ('last_login', 'date_joined')
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'business_name', 'phone_number')
        }),
        ('Address', {
            'fields': ('country', 'street_address', 'town', 'state', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_seller', 'is_customer', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Password Reset', {
            'fields': ('reset_code', 'reset_code_expires'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )


admin.site.site_header = "E-commerce Admin"
admin.site.site_title = "E-commerce Administration"
admin.site.index_title = "Welcome to E-commerce Admin"

# from django.contrib import admin
# from .models import Category, Product, ProductImage, Order, OrderItem, NewsletterSubscription, Banner
# from .models import Banner, Cart, CartItem 

# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     prepopulated_fields = {"slug": ("name",)}
#     list_display = ("name", "slug")
#     search_fields = ("name",)
#     ordering = ("name",)


# class ProductImageInline(admin.TabularInline):
#     model = ProductImage
#     extra = 0
#     max_num = 4  


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     prepopulated_fields = {"slug": ("name",)}
#     list_display = ("name", "price", "stock", "is_featured", "category", "created_at")
#     list_filter = ("is_featured", "category")
#     search_fields = ("name", "description")
#     ordering = ("-created_at",)
#     inlines = [ProductImageInline] 


# class OrderItemInline(admin.TabularInline):
#     model = OrderItem
#     extra = 0


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     inlines = [OrderItemInline]
#     list_display = ("id", "customer_name", "status", "created_at")
#     list_filter = ("status", "created_at")
#     search_fields = ("customer_name", "customer_email")
#     ordering = ("-created_at",)


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ("product", "quantity", "price", "order")
#     list_filter = ("product",)


# @admin.register(NewsletterSubscription)
# class NewsletterSubscriptionAdmin(admin.ModelAdmin):
#     list_display = ("email", "subscribed_at")
#     search_fields = ("email",)
#     ordering = ("-subscribed_at",)


# @admin.register(Banner)
# class BannerAdmin(admin.ModelAdmin):
#     list_display = ('title', 'is_active', 'created_at')
#     list_filter = ('is_active', 'created_at')
#     search_fields = ('title', 'subtitle')


# class CartItemInline(admin.TabularInline):
#     model = CartItem
#     extra = 0
#     readonly_fields = ('get_total_price', 'added_at')
#     fields = ('product', 'quantity', 'get_total_price', 'added_at')
    
#     def get_total_price(self, obj):
#         return f"${obj.get_total_price():.2f}"
#     get_total_price.short_description = 'Total Price'


# @admin.register(Cart)
# class CartAdmin(admin.ModelAdmin):
#     list_display = ('id', 'get_total_quantity', 'get_total_price', 'created_at', 'updated_at')
#     list_filter = ('created_at', 'updated_at')
#     search_fields = ('id',)
#     readonly_fields = ('id', 'created_at', 'updated_at', 'get_total_price_display', 'get_total_quantity_display')
#     inlines = [CartItemInline]
#     ordering = ('-created_at',)
    
#     fieldsets = (
#         ('Cart Information', {
#             'fields': ('id', 'created_at', 'updated_at')
#         }),
#         ('Cart Summary', {
#             'fields': ('get_total_quantity_display', 'get_total_price_display'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_total_quantity(self, obj):
#         return obj.get_total_quantity()
#     get_total_quantity.short_description = 'Total Items'
    
#     def get_total_price(self, obj):
#         return f"${obj.get_total_price():.2f}"
#     get_total_price.short_description = 'Total Value'
    
#     def get_total_price_display(self, obj):
#         return f"${obj.get_total_price():.2f}"
#     get_total_price_display.short_description = 'Total Cart Value'
    
#     def get_total_quantity_display(self, obj):
#         return obj.get_total_quantity()
#     get_total_quantity_display.short_description = 'Total Items in Cart'

#     def has_add_permission(self, request):
#         return False


# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#     list_display = ('id', 'cart', 'product', 'quantity', 'get_total_price', 'added_at')
#     list_filter = ('added_at', 'cart', 'product')
#     search_fields = ('cart__id', 'product__name')
#     readonly_fields = ('added_at', 'get_total_price_display')
#     list_select_related = ('cart', 'product')
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('cart', 'product', 'quantity')
#         }),
#         ('Price Information', {
#             'fields': ('get_total_price_display',),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': ('added_at',),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_total_price(self, obj):
#         return f"${obj.get_total_price():.2f}"
#     get_total_price.short_description = 'Total Price'
    
#     def get_total_price_display(self, obj):
#         return f"${obj.get_total_price():.2f}"
#     get_total_price_display.short_description = 'Total Price'
    
#     def has_add_permission(self, request):
#         return False


# admin.site.site_header = "E-commerce Admin"
# admin.site.site_title = "E-commerce Administration"
# admin.site.index_title = "Welcome to E-commerce Admin"