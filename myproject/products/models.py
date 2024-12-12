from django.db import models
from decimal import Decimal, InvalidOperation
from django.conf import settings

# Create your models here.
class Categories(models.Model):
    brand_name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, default='listed')
    offer = models.DecimalField(max_digits=8, decimal_places=2, default=0) 
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    def __str__(self):
        return self.brand_name 
    
class Types(models.Model):
    category = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, default='listed')
    offer = models.DecimalField(max_digits=8, decimal_places=2, default=0,) 
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    def __str__(self):
        return self.category 
 
class Size(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name
 

  

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ratings = models.FloatField(default=0.0)
    comments = models.TextField(blank=True)
    size = models.ManyToManyField(Size, related_name='products')
    status = models.CharField(max_length=10, default='listed') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)   
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)  
    offer = models.DecimalField(max_digits=8, decimal_places=2, default=0) 
    category = models.ForeignKey('Categories', on_delete=models.CASCADE,null=True,blank=True )      
    Types = models.ForeignKey('Types', on_delete=models.CASCADE,null=True,blank=True )      
    def __str__(self):
        return self.name
    
    
    @property
    def discounted_price(self):
        """Calculates the price after the discount."""
        if self.offer > 0:
            discount = (self.offer / 100) * self.original_price
            return self.original_price - discount
        return self.original_price   

    def save(self, *args, **kwargs):
       """Override the save method to store the discounted price in the database."""
       try:
           
           offer_value = Decimal(self.offer) if self.offer else Decimal(0)
           original_price_value = Decimal(self.original_price) if self.original_price else Decimal(0)
   
           if offer_value > 0:
               discount = (offer_value / Decimal(100)) * original_price_value
               self.price = original_price_value - discount
           else:
               self.price = original_price_value
   
       except (ValueError, InvalidOperation):
           self.price = Decimal('0.00')   
   
       super(Product, self).save(*args, **kwargs)

    
    
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='additional_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/extra/')


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.size.name} - {self.stock} in stock"
    
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')   
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"