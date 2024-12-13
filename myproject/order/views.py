from django.shortcuts import render, get_object_or_404
from .models import OrderItem,Order
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from products.models import  ProductSize
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from wallet.models import Wallet,Transaction
import uuid
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
import razorpay
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa


def admin_required(function):
    return user_passes_test(
        lambda user: user.is_superuser,
        login_url='misc_pages:custom_404')(function)
 

@never_cache

@login_required(login_url='authentication:login')
def order(request, order_id=None):
    if order_id:
       
        selected_order = get_object_or_404(Order, order_id=order_id, user=request.user)
        order_items = OrderItem.objects.filter(order=selected_order)
     
        total_price_in_paise = int(selected_order.total_price * 100)
        coupon = None
        if selected_order.coupon_code:
            coupon = Coupon.objects.filter(code=selected_order.coupon_code).first()

        print('coupon:',coupon)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create(dict(
                amount=total_price_in_paise,   
                currency='INR',
                payment_capture='1'
            ))
        razorpay_order_id = razorpay_order['id']
        selected_order.razorpay_order_id = razorpay_order_id
        selected_order.save()

        context = {
            'orders': None,
            'order_items': order_items,
            'selected_order': selected_order,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'total_price_in_paise': total_price_in_paise,
            'order_id': selected_order.order_id,
            'coupon':coupon
        }

    else:
        
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        order_items = None

        context = {
            'orders': orders,
            'order_items': order_items,
            'selected_order': None,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
        }

    return render(request, 'order/order.html', context)

def download_invoice(request, order_id):
    order = Order.objects.get(order_id=order_id)
    order_items = order.items.exclude(status='Cancelled')
    total_price = sum(item.subtotal_price for item in order_items)
    total_price_after_discount = order.total_price
    print('total_price_after_discount:',total_price_after_discount)
    discount_amount = total_price-total_price_after_discount
    print('discount_amount:',discount_amount)
    context = {
        'order': order,
        'order_items': order_items,
        'total_price':total_price,
        # 'coupon_code': coupon_code,   
        'discount_amount': discount_amount ,
        'total_after_discount':total_price_after_discount
    }
    html_content = render_to_string('order/invoice.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    pisa_status = pisa.CreatePDF(html_content, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response

@never_cache
@admin_required
def order_admin(request):
    search_query = request.GET.get('search', '')
    sort_field = request.GET.get('sort', '-order_id')   

    orders = Order.objects.filter(items__isnull=False)

    if search_query:
        orders = orders.filter(order_id__icontains=search_query)   

    orders = orders.order_by(sort_field)

    paginator = Paginator(orders, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'orders': page_obj,
        'search_query': search_query,
        'sort_field': sort_field,  
    }
    return render(request, 'order/order_admin.html', context)

@never_cache
@admin_required
def order_admin(request, order_id=None):
    search_query = request.GET.get('search', '')
    sort_field = request.GET.get('sort', '-order_id')

    orders = Order.objects.filter(items__isnull=False)

    if search_query:
        orders = orders.filter(
           Q(user__username__icontains=search_query) |   
           Q(tracking_number__icontains=search_query)
        )    
    orders = orders.order_by(sort_field)

    paginator = Paginator(orders, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if order_id:
        order = get_object_or_404(Order, order_id=order_id)
        shipping_address = order.shipping_address
        order_items = OrderItem.objects.filter(order=order).order_by('-orderitem_id')
        context = {
             'order_items': order_items,
            'selected_order_id': order.order_id,
            'shipping_address': shipping_address,
         
        }
        return render(request, 'order/order_admin.html', context)
    orders = Order.objects.all().order_by('-order_id') 
    context = {
        'orders': page_obj,
        'search_query': search_query,
        'sort_field': sort_field,
        }
    return render(request, 'order/order_admin.html', context)

@never_cache




def update_orderitem_status(request, orderitem_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        print("Starting update_orderitem_status...")

        # Use the correct field name 'orderitem_id'
        order_item = get_object_or_404(OrderItem, orderitem_id=orderitem_id)
        print('order_item:',order_item)
        print('order_item id:',order_item.orderitem_id)
        new_status = request.POST.get('status')
        print('new_status:',new_status)
        return_reason = request.POST.get('return_reason', '')   
        order_item.status = new_status
        order_item.save()
        print(f"Order item: {order_item}, New status: {new_status}, Return reason: {return_reason}")

        if not new_status:
            return JsonResponse({'error': 'Status is required'}, status=400)

        transaction_instance = None  

        
        with transaction.atomic():
            if order_item.status == "Cancelled":
                print("Processing cancellation...")

                product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
                product_size.stock += order_item.quantity
                product_size.save()
                print(f"Restocked product size: {product_size}")

                
                wallet, _ = Wallet.objects.get_or_create(user=order_item.order.user)
                if wallet.add_funds(order_item.subtotal_price):
                    transaction_id = str(uuid.uuid4().hex[:8])
                    transaction_instance = Transaction.objects.create(
                        user=order_item.order.user,
                        transaction_id=transaction_id,
                        amount=order_item.subtotal_price,
                        status='Completed',
                        transaction_type='Credit'
                    )
                    print(f"Transaction created: {transaction_instance.transaction_id}")
                    messages.success(request, f"Order item cancelled and ${order_item.price} added to your wallet!")
                else:
                    print("Failed to add funds to wallet.")
                    return JsonResponse({'error': 'Failed to add funds to wallet'}, status=500)

            elif new_status == "Requested Return":
                print("Processing return approval...")
 
                product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
                product_size.stock += order_item.quantity
                product_size.save()
                print(f"Restocked product size: {product_size}")

               
                wallet, _ = Wallet.objects.get_or_create(user=order_item.order.user)
                if wallet.add_funds(order_item.price):
                    transaction_id = str(uuid.uuid4().hex[:8])
                    transaction_instance = Transaction.objects.create(
                        user=order_item.order.user,
                        transaction_id=transaction_id,
                        amount=order_item.price, 
                        status='Completed',
                        transaction_type='Credit'
                    )
                    print(f"Transaction created for return: {transaction_instance.transaction_id}")
                    messages.success(request, f"Order item returned and ${order_item.price} credited to your wallet!")
                else:
                    print("Failed to add funds for return.")
                    return JsonResponse({'error': 'Failed to add funds to wallet for return'}, status=500)

            
            order_item.status = new_status
            order_item.save()
            print(f"Order item status updated to {new_status}")

          
            if transaction_instance:
                print(f"Transaction ID: {transaction_instance.transaction_id}")

             
            return redirect('order:orders') 

    except Exception as e:
       
        print(f"Error occurred: {e}") 

      
        return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)
@never_cache
# @admin_required

def update_return_orderitem_status(request, orderitem_id):
    if request.method == 'POST':
        try:
            
            print("POST Request Data:", request.POST)
             
            order_item = get_object_or_404(OrderItem, orderitem_id=orderitem_id)
            new_status = request.POST.get('status')
            return_reason = request.POST.get('return_reason', '')   
            
            
            print(f"Order Item: {order_item}, New Status: {new_status}, Return Reason: {return_reason}")

            if not new_status:
                return JsonResponse({'error': 'Status is required'}, status=400)

            if new_status == "Approve Returned":
                
                product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
                product_size.stock += order_item.quantity
                product_size.save()

               
                order_item.return_reason = return_reason
                order_item.save()

            
            order_item.status = new_status
            order_item.save()

           
            response = JsonResponse({'message': 'Order item return request updated successfully!', 'new_status': new_status}, status=200)

          
            print("Response being returned:", response)

             
            return response

        except Exception as e:
           
            print(f"Error occurred: {str(e)}")  

           
            return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)

    else:
         
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    
    
