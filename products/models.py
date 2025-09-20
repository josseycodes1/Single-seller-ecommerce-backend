from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser, BaseUserManager
import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  
    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=255, blank=True)  
    is_seller = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)
    reset_code = models.CharField(max_length=6, blank=True, null=True)
    reset_code_expires = models.DateTimeField(blank=True, null=True)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [] 

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def generate_reset_code(self):
        """Generate a 6-digit numerical reset code"""
        code = str(random.randint(100000, 999999))
        self.reset_code = code
        self.reset_code_expires = timezone.now() + timedelta(minutes=59) 
        self.save()
        return code

    def is_reset_code_valid(self, code):
        """Check if the reset code is valid and not expired"""
        if (self.reset_code == code and 
            self.reset_code_expires and 
            self.reset_code_expires > timezone.now()):
            return True
        return False

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    stock = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    colors = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="List of available colors, e.g. ['Red', 'Blue', 'Black']"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        related_name="images", 
        on_delete=models.SET_NULL,  
        null=True, 
        blank=True
    )
    image = CloudinaryField('image')

    def __str__(self):
        return f"Image for {self.product.name if self.product else 'No Product'}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]

    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)
    customer_address = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Banner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True, null=True) 
    button_text = models.CharField(max_length=50, default="Buy now") 
    discount_text = models.CharField(max_length=100, blank=True, null=True)  
    image = CloudinaryField('image', blank=True, null=True) 
    image_mobile = CloudinaryField('image_mobile', blank=True, null=True) 
    secondary_image = CloudinaryField('secondary_image', blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
