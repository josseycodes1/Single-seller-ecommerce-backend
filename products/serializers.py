from rest_framework import serializers
from .models import Category, Product, Order, OrderItem, NewsletterSubscription, Banner, ProductImage, Cart, CartItem, Payment
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils.text import slugify
from rest_framework import serializers
from .models import Product, CartItem
import json
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
      
        token["email"] = user.email
        token["is_seller"] = user.is_seller
        token["business_name"] = user.business_name
        print(f"Token created for user: {user.email}, is_seller: {user.is_seller}")  # Debug
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
      
        data.update({
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "business_name": self.user.business_name,
            "is_seller": self.user.is_seller,
        })
        print(f"Token response for user: {self.user.email}, is_seller: {self.user.is_seller}")  # Debug
        return data

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        reset_code = user.generate_reset_code()
        return reset_code

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs['email']
        code = attrs['code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        
        if not user.is_reset_code_valid(code):
            raise serializers.ValidationError({"code": "Invalid or expired reset code."})
        
        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        
        user.set_password(new_password)
        user.reset_code = None
        user.reset_code_expires = None
        user.save()
        
        return user
    
class PasswordResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        reset_code = user.generate_reset_code()
        return reset_code, email

User = get_user_model()

class SellerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        error_messages={
            "min_length": "Password must be at least 8 characters long."
        }
    )

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "business_name"]

    def validate_email(self, value):
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(char in "!@#$%^&*()-_=+[]{};:,.<>?/|`~" for char in value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        return value

    def validate(self, attrs):
        if not attrs.get("first_name"):
            raise serializers.ValidationError({"first_name": "First name is required."})
        if not attrs.get("last_name"):
            raise serializers.ValidationError({"last_name": "Last name is required."})
        if not attrs.get("business_name"):
            raise serializers.ValidationError({"business_name": "Business name is required."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            business_name=validated_data.get("business_name", ""),
            is_seller=True
        )
        user.is_seller = True
        user.is_customer = False
        user.save()
        return user
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True}
        }
    
    def create(self, validated_data):
        if 'slug' not in validated_data or not validated_data['slug']:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'name' in validated_data and validated_data['name'] != instance.name:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)
class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image_url"]

    def get_image_url(self, obj):
     
        if obj.image:
            return obj.image.url
        return None  
    
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False, read_only=True)
    image_files = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    offer_price = serializers.SerializerMethodField(required=False)
    avg_rating = serializers.FloatField(source='rating', read_only=True) 
    colors = serializers.JSONField() 
    category = CategorySerializer(read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "price", "offer_price", "description",
            "stock", "rating", "avg_rating", "is_featured",
            "created_at", "updated_at", "images", "image_files", "category", "colors",
            "category_id"
        ]
        read_only_fields = ["slug", "created_at", "updated_at", "avg_rating", "images"]

    def create(self, validated_data):
        image_files = validated_data.pop('image_files', [])
        
        product = super().create(validated_data)
        
        for image_file in image_files:
            ProductImage.objects.create(product=product, image=image_file)
            
        return product

    def update(self, instance, validated_data):
        image_files = validated_data.pop('image_files', [])
    
        product = super().update(instance, validated_data)
        
        for image_file in image_files:
            ProductImage.objects.create(product=product, image=image_file)
            
        return product

    def get_offer_price(self, obj):
        return float(obj.price)

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Product name must be at least 3 characters long.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock cannot be negative.")
        return value

    def validate_colors(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Colors must be a list of strings.")
        for color in value:
            if not isinstance(color, str):
                raise serializers.ValidationError("Each color must be a string.")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = '__all__'
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscription
        fields = '__all__'
class BannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    image_mobile = serializers.SerializerMethodField()
    secondary_image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = '__all__'

    def get_image(self, obj):
        return obj.image.url if obj.image else None

    def get_image_mobile(self, obj):
        return obj.image_mobile.url if obj.image_mobile else None

    def get_secondary_image(self, obj):
        return obj.secondary_image.url if obj.secondary_image else None

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        source='product', 
        write_only=True
    )
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total_price', 'added_at', 'color']
        read_only_fields = ['id', 'added_at']

    def get_total_price(self, obj):
        return obj.get_total_price()

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'total_quantity', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_total_quantity(self, obj):
        return obj.get_total_quantity()

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    color = serializers.CharField(required=True)

    def validate(self, attrs):
        product_id = attrs.get('product_id')
        color = attrs.get('color')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            error = {"product_id": "Product does not exist"}
            print("AddToCartSerializer error:", json.dumps(error))
            raise serializers.ValidationError(error)

        if product.stock <= 0:
            error = {"product_id": "Product is out of stock"}
            print("AddToCartSerializer error:", json.dumps(error))
            raise serializers.ValidationError(error)

        # Validate color
        if product.colors and color not in product.colors:
            error = {"color": f"Invalid color. Available colors: {product.colors}"}
            print("AddToCartSerializer error:", json.dumps(error))
            raise serializers.ValidationError(error)

        # Attach product instance to validated_data for later use
        attrs['product'] = product
        return attrs

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    color = serializers.CharField(required=False)  

    def validate(self, attrs):
       
        cart_item = self.context.get('cart_item')
        if cart_item and 'color' in attrs:
            product = cart_item.product
            color = attrs['color']
            
            
            if product.colors and color not in product.colors:
                raise serializers.ValidationError({
                    "color": f"Invalid color. Available colors: {product.colors}"
                })
        
        return attrs
    
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_reference', 'paystack_reference', 'status', 'created_at', 'updated_at']

class InitializePaymentSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    email = serializers.EmailField()
    order_id = serializers.IntegerField() 
    callback_url = serializers.URLField(required=False, allow_blank=True)

    def validate(self, attrs):
        cart_id = attrs['cart_id']
        order_id = attrs['order_id']
        
        try:
            cart = Cart.objects.get(id=cart_id)
            order = Order.objects.get(id=order_id)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"cart_id": "Cart not found"})
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order_id": "Order not found"})
        
        if not cart.items.exists():
            raise serializers.ValidationError({"cart_id": "Cart is empty"})
        
        attrs['cart'] = cart
        attrs['order'] = order  
        return attrs

class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)

class CheckoutSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    email = serializers.EmailField()
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=20)
    address = serializers.JSONField()
    order_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_address(self, value):
        required_fields = ['country', 'street_address', 'town', 'state', 'postal_code']
        for field in required_fields:
            if field not in value or not value[field]:
                raise serializers.ValidationError(f"Address field '{field}' is required")
        return value