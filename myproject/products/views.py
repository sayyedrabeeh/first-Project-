from django.shortcuts import render
from .models import Categories,Product,ProductImage, Size,ProductSize,Types
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.db.models import Count, Avg, Sum
from django.urls import reverse
from django.core.files.base import ContentFile
import base64
import json
from django.db.models import F
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from cart.models import CartItem
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from decimal import Decimal, InvalidOperation
from .models import Wishlist 

def admin_required(function):
    return user_passes_test(
        lambda user: user.is_superuser,
        login_url='misc_pages:custom_404')(function)
def home(request):
    products = Product.objects.filter(status='listed')
    catogery = Categories.objects.filter(status='listed')
    page_number = request.GET.get('page', 1)
    if request.user.is_authenticated:
        cart_items_count = CartItem.objects.filter(cart__user=request.user).count()
    else:
        cart_items_count = 0  
    product = None
    if 'product_id' in request.GET:
        product_id = request.GET['product_id']
        product = get_object_or_404(Product, id=product_id)
    paginator = Paginator(products, 12)
    try:
        paginated_products = paginator.page(page_number)
    except PageNotAnInteger:
        paginated_products = paginator.page(1)  
    except EmptyPage:
        paginated_products = paginator.page(paginator.num_pages) 
    context = {
        'catogery': catogery,
        'products': paginated_products,
        'product': product,
        'cart_items_count': cart_items_count,
    }
    return render(request, 'products/home.html', context)
@never_cache
@login_required(login_url='authentication:login')
def products(request):
    query = request.GET.get('q', '')  
    sort_by = request.GET.get('sort', 'default')   
    page_number = request.GET.get('page', 1)  

    # Filter by selected categories (multiple categories allowed)
    category_ids = request.GET.getlist('category')
    if category_ids:
        products = Product.objects.filter(category__id__in=category_ids, status='listed')
    else:
        products = Product.objects.filter(status='listed')

    # Filter by selected brands (multiple brands allowed)
    brand_names = request.GET.getlist('brand')
    if brand_names:
        products = products.filter(category__brand_name__in=brand_names)

    # Filter by price range (if provided)
    min_price = request.GET.get('min_price', None)
    max_price = request.GET.get('max_price', None)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Filter by query search
    if query:
        products = products.filter(name__icontains=query)

    # Sorting logic
    if sort_by == 'popularity':
        products = products.annotate(popularity=Count('comments')).order_by('-popularity')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('ratings')).order_by('-avg_rating')
    elif sort_by == 'newness':
        products = products.order_by('-created_at')
    elif sort_by == 'price_low_to_high':
        products = products.order_by('price')
    elif sort_by == 'price_high_to_low':
        products = products.order_by('-price')
    elif sort_by == 'a_z':
        products = products.order_by('name')
    elif sort_by == 'z_a':
        products = products.order_by('-name')

    # Pagination
    paginator = Paginator(products, 12)
    try:
        paginated_products = paginator.page(page_number)
    except PageNotAnInteger:
        paginated_products = paginator.page(1)
    except EmptyPage:
        paginated_products = paginator.page(paginator.num_pages)

  
    categories = Categories.objects.filter(status='listed').order_by('-id')
    Type=Types.objects.filter(status='listed').order_by('-id')

  
    cart_items_count = CartItem.objects.filter(cart__user=request.user).count()

  
    context = {
        'products': paginated_products,
        'categories': categories,
        'query': query,
        'Type':Type,
        'sort_by': sort_by,
        'cart_items_count': cart_items_count,
        'min_price': min_price,
        'max_price': max_price,
        'category_ids': category_ids,
        'brand_names': brand_names,
    }

    return render(request, 'products/products.html', context)
@never_cache
@login_required(login_url='authentication:login')
def products_detail(request, id):
    product = get_object_or_404(Product, id=id)
    sizes_with_stock = ProductSize.objects.filter(product=product).select_related('size').order_by('size__id') 
    print('sizes_with_stock:',sizes_with_stock)
    cart_items_count = CartItem.objects.filter(cart__user=request.user).count()
    categories = Categories.objects.filter(status='listed').order_by('-id')
    sizes_stock = [
        {
            'id': ps.size.id,
            'name': ps.size.name,
            'stock': ps.stock
        }
        for ps in sizes_with_stock
    ]
    context = {
        'product': product,
        'sizes_stock': sizes_stock,
        'cart_items_count': cart_items_count,
        'categories':categories
    }
    return render(request, 'products/product_detail.html', context)
@login_required(login_url='authentication:login')    
def brand_products(request, brand_name):
    products = Product.objects.filter(category__brand_name=brand_name,status='listed')
    context = {
        'products': products,
        'brand_name': brand_name
    }
    return render(request, 'products/brand_products.html', context)
@never_cache
@admin_required
def catogery(request):
    action=request.POST.get('action')
    if request.method=='POST':
        if action =='add':
            brand_name=request.POST.get('brand_name')
            offer=request.POST.get('offer',0)
            status=request.POST.get('status','True')
            if not brand_name:
                messages.error(request, "Brand name is required.")
                return redirect('products:catogery')

            if Categories.objects.filter(brand_name__iexact=brand_name).exists():
                messages.error(request, "A category with this brand name already exists.")
                return redirect('products:catogery')
            try:
                if offer == '':
                    offer = 0   
                else:
                    offer = Decimal(offer)
                if offer < 0 or offer > 100:
                    raise ValueError("Offer must be between 0 and 100.")
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f"Invalid offer: {e}")
                return redirect('products:catogery')

            catogery=Categories.objects.create(
                brand_name=brand_name,
                active=status,
                offer=offer
            )
            catogeryimage = request.FILES.get('catogeryimage')
            print("catogeryimage:",catogeryimage)
            if catogeryimage:
                try:
                    catogery.image.save(catogeryimage.name, catogeryimage)
                except Exception as e:
                    print(f"Error saving image: {e}")
            messages.success(request, "Category added successfully!")
            return redirect('products:catogery')
        elif action=='edit'  :
            print('hi')
            catogery_id=request.POST.get('catogery_id')
            catogery=get_object_or_404(Categories,id=catogery_id)
            catogery.brand_name=request.POST.get('brand_name')
            catogery.offer=request.POST.get('offer')
            catogery.active=request.POST.get('active','True')
            catogery.save()
            image = request.FILES.get('image')
            if image:
                catogery.image.save(image.name, image)
                catogery.save()
                print('catogery:',catogery)
            return redirect('products:catogery')
        elif action =='toggle':
            catogery_id=request.POST.get('catogery_id')
            catogery=get_object_or_404(Categories,id=catogery_id)
            if catogery.status=='listed':
                catogery.status='dislisted'
            else:
                catogery.status='listed'
            catogery.save()
        return redirect('products:catogery')
    error_message = None
    modal_open = False
    search_query = request.GET.get('search', '')
    categories = Categories.objects.all()
    if search_query:
        categories = categories.filter(brand_name__icontains=search_query)
    sort_field = request.GET.get('sort', '-id')   
    categories = categories.order_by(sort_field)
    paginator = Paginator(categories, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'categories': page_obj,
        'error_message': error_message,
        'modal_open': modal_open,
        'search_query': search_query,
        'sort_field': sort_field,
    }
    return render(request, 'products/catogery.html', context)

def Type(request):
    print('shitttttttttttttttt')
    action=request.POST.get('action')
    if request.method=='POST':
        if action =='add':
            category=request.POST.get('category')
            offer=request.POST.get('offer')
            status=request.POST.get('status','True')
               
            if not category:
                messages.error(request, "Category name is required.")
                return redirect('products:Type')

            if Types.objects.filter(category__iexact=category).exists():
                messages.error(request, "A type with this category name already exists.")
                return redirect('products:Type')

            try:
                if offer == '':
                    offer = 0   
                else:
                    offer = Decimal(offer)
                if offer < 0 or offer > 100:
                    raise ValueError("Offer must be between 0 and 100.")
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f"Invalid offer: {e}")
                return redirect('products:catogery')

             
            catogery=Types.objects.create(
                category=category,
                active=status,
                offer=offer
            )
            catogeryimage = request.FILES.get('catogeryimage')
            print("catogeryimage:",catogeryimage)
            if catogeryimage:
                try:
                    catogery.image.save(catogeryimage.name, catogeryimage)
                except Exception as e:
                    print(f"Error saving image: {e}")
            messages.success(request, "Category added successfully!")
            return redirect('products:Type')
        elif action=='edit'  :
            print('hi')
            catogery_id=request.POST.get('catogery_id')
            catogery=get_object_or_404(Types,id=catogery_id)
            catogery.category=request.POST.get('category')
            catogery.offer=request.POST.get('offer')
            catogery.active=request.POST.get('active','True')
            catogery.save()
            image = request.FILES.get('image')
            if image:
                catogery.image.save(image.name, image)
                catogery.save()
                print('catogery:',catogery)
            return redirect('products:Type')
        elif action =='toggle':
            catogery_id=request.POST.get('catogery_id')
            print('catogery_id:',catogery_id)
            catogery=get_object_or_404(Types,id=catogery_id)
            if catogery.status=='listed':
                catogery.status='dislisted'
            else:
                catogery.status='listed'
            catogery.save()
        return redirect('products:Type')
    error_message = None
    modal_open = False
    search_query = request.GET.get('search', '')
    categories = Types.objects.all()
    if search_query:
        categories = categories.filter(brand_name__icontains=search_query)
    sort_field = request.GET.get('sort', '-id')   
    categories = categories.order_by(sort_field)
    paginator = Paginator(categories, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'categories': page_obj,
        'error_message': error_message,
        'modal_open': modal_open,
        'search_query': search_query,
        'sort_field': sort_field,
    }
    return render(request, 'products/Type.html', context)

@login_required(login_url='authentication:login')    
def wishlist(request,action,product_id=None):
    if action=='view':
         wishlist_items = Wishlist.objects.filter(user=request.user)
         return render(request, 'products/wishlist.html', {'wishlist_items': wishlist_items})
    elif action=='add' and product_id:
        product = get_object_or_404(Product, id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        messages.success(request, f"{product.name} has been added to your wishlist!")
        return redirect('products:wishlist','view')  
    elif action =='remove' and product_id:
            product = get_object_or_404(Product, id=product_id)
            wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
            if wishlist_item:
                wishlist_item.delete()
                messages.success(request, f"{product.name} has been removed from your wishlist.")
            else:
                messages.info(request, f"{product.name} was not in your wishlist.")
            return redirect('products:wishlist','view')
    messages.error(request, "Invalid action.")
    return redirect('products:wishlist','view')       
@never_cache
@admin_required 
def products_admin(request):
    if request.method =='POST':
        action=request.POST.get('action')
        if action =='add':
            product_name=request.POST.get('product_name')
            size_data = request.POST.getlist('size')
 
            try:
                price = Decimal(request.POST.get('price', '0'))  
            except InvalidOperation:
                price = Decimal('0')   
    
            try:
                offer = Decimal(request.POST.get('offer', '0'))   
            except InvalidOperation:
                offer = Decimal('0')
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category')
            Type_id = request.POST.get('Type')
            category = Categories.objects.get(id=category_id) if category_id else None
            Type = Types.objects.get(id=Type_id) if Type_id else None
            product = Product.objects.create(
              name=product_name,
              description=description,
              original_price=price,
              offer=offer,
              category=category,
              Types=Type,
          )
            for size in size_data:
               size_stock = request.POST.get(f'stock_{size}')
               if size_stock:
                  try:
                      size_obj, created = Size.objects.get_or_create(name=size)
                      ProductSize.objects.create(product=product, size=size_obj, stock=int(size_stock))
                  except Size.DoesNotExist:
                      messages.error(request, f"Size '{size}' does not exist.")
                  except ValueError:
                      messages.error(request, f"Invalid stock value for size '{size}'.")            
            cropped_images_data = request.POST.get('cropped_images')
            if cropped_images_data:
               cropped_images = json.loads(cropped_images_data)
               for image_data in cropped_images:
                   image_content = ContentFile(base64.b64decode(image_data.split(",")[1]), name='product_image')
                   ProductImage.objects.create(product=product, image=image_content)
            return redirect('products:products_admin')
        elif action == "edit":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, id=product_id)
            product.name = request.POST.get("name")
            product.category_id = request.POST.get("category")
            product.Types_id = request.POST.get("Type")
            product.original_price = Decimal(request.POST.get("price", 0))
            product.offer = Decimal(request.POST.get("offer", 0))
            product.description = request.POST.get("description", "").strip()
            product.save()
            sizes = ["XS", "S", "M", "L", "XL"]
            for size in sizes:
                size_stock = request.POST.get(f'stock_{size}')
                if size_stock:
                    try:
                        size_obj = Size.objects.get(name=size)
                        product_size, created = ProductSize.objects.get_or_create(product=product, size=size_obj)
                        product_size.stock = int(size_stock)
                        product_size.save()
                    except Size.DoesNotExist:
                        messages.error(request, f"Size '{size}' does not exist.")
                    except ValueError:
                        messages.error(request, f"Invalid stock value for size '{size}'.")
            messages.success(request, "Product updated successfully!")
            return redirect("products:products_admin")
        elif action == "toggle_status":
                 product_id = request.POST.get("product_id")
                 product = get_object_or_404(Product, id=product_id)
                 product.status = "listed" if product.status == "dislisted" else "dislisted"
                 product.save()
                 messages.success(request, f"Product status changed to {product.status}!")
                 return redirect("products:products_admin")
    categories = Categories.objects.all().order_by("-id")
    Type = Types.objects.all().order_by("-id")
    products = Product.objects.prefetch_related("category").all().order_by("-id")
    sizes = Size.objects.all()  
    for product in products:
        product_sizes = ProductSize.objects.filter(product=product)
        total_stock = product_sizes.aggregate(Sum("stock"))["stock__sum"] or 0
        product.total_stock = total_stock
        product.size_stock = [{"size_name": ps.size.name, "stock": ps.stock} for ps in product_sizes]
    context={
        'categories':categories,
        'Types':Type,
        'products':products,
        'sizes':sizes,
        
    }
    return render(request, 'products/products_admin.html',context)