from rest_framework import serializers
from .models import Category, Product, Order, OrderItem, NewsletterSubscription, Banner, ProductImage
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from django.utils.text import slugify
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
    offer_price = serializers.SerializerMethodField(required=False)
    avg_rating = serializers.FloatField(source='rating', read_only=True) 

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "price", "offer_price", "description",
            "stock", "rating", "avg_rating", "is_featured",
            "created_at", "updated_at", "images", "category", "colors"
        ]
        read_only_fields = ["slug", "created_at", "updated_at", "avg_rating"]
    
    def get_offer_price(self, obj):
        return float(obj.price)

    def create(self, validated_data):
       
        request = self.context.get('request')
        images_data = request.FILES.getlist('images') if request else []
        
        if len(images_data) > 4:
            raise serializers.ValidationError("A product can have at most 4 images.")
        
        product = Product.objects.create(**validated_data)
        
       
        for image_data in images_data:
            ProductImage.objects.create(product=product, image=image_data)
        
        return product

    def update(self, instance, validated_data):
        request = self.context.get('request')
        images_data = request.FILES.getlist('images') if request else []

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data:
            existing_count = instance.images.count()
            if existing_count + len(images_data) > 4:
                raise serializers.ValidationError(
                    f"Cannot add {len(images_data)} images. "
                    f"Product already has {existing_count}, max allowed is 4."
                )
            for image_data in images_data:
                ProductImage.objects.create(product=instance, image=image_data)

        return instance
    
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

