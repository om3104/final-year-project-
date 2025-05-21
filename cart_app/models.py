from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal

class User(AbstractUser):
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    REQUIRED_FIELDS = ['phone_number']

class RFIDCard(models.Model):
    card_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.card_id

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    weight = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], help_text="Weight in kilograms")
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    rfid_card = models.OneToOneField(RFIDCard, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_weight = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'), help_text="Total weight of items in cart in kilograms")
    is_active = models.BooleanField(default=True)

    def update_total_weight(self):
        total = Decimal('0.000')
        for item in self.items.all():
            total += item.product.weight * item.quantity
        self.total_weight = total
        self.save()

    def check_weight_discrepancy(self, actual_weight):
        """
        Check if there's a discrepancy between expected and actual weight
        Returns True if fraud is detected, False otherwise
        """
        # Allow for a small margin of error (e.g., 50g)
        margin_of_error = Decimal('0.050')
        expected_weight = self.total_weight
        
        if abs(actual_weight - expected_weight) > margin_of_error:
            self.fraud_detected = True
            self.fraud_message = f"Weight exceeds limit by {abs(actual_weight - expected_weight):.3f} kg ({abs((actual_weight - expected_weight) / expected_weight) * 100:.1f}% more than expected)! Please remove some items."
            self.save()
            return True
        return False

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at the time of purchase
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'}"

    @property
    def subtotal(self):
        return self.quantity * self.price

class CartWeight(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='weight_records')
    actual_weight = models.DecimalField(max_digits=10, decimal_places=3, help_text="Actual weight measured from the scale in kilograms")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Weight: {self.actual_weight}kg at {self.timestamp}" 