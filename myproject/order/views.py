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
from decimal import Decimal
from django.urls import reverse


def admin_required(function):
    return user_passes_test(
        lambda user: user.is_superuser,
        login_url='misc_pages:custom_404')(function)
 

# @never_cache

@login_required(login_url='authentication:login')
def order(request, order_id=None):
   
    if order_id:
       
        selected_order = get_object_or_404(Order, order_id=order_id, user=request.user)
 
        order_items = OrderItem.objects.filter(order=selected_order)
 

        total_subtotal_price = sum(item.subtotal_price for item in order_items)
        cupon_discount = Decimal(total_subtotal_price) - Decimal(selected_order.total_price)
        total_price_in_paise = int(selected_order.total_price * 100)
        coupon = None
        if selected_order.coupon_code:
            coupon = Coupon.objects.filter(code=selected_order.coupon_code).first()
        updated_total_price = None
        if 'updated_total_price' in request.GET:
          updated_total_price = request.GET.get('updated_total_price')
         
  
        if updated_total_price:
            updated_total_price = Decimal(updated_total_price)
        else:
            updated_total_price = Decimal(selected_order.total_price)

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
            'coupon':coupon,
            'cupon_discount':cupon_discount,
            'updated_total_price':updated_total_price
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
    discount_amount = total_price-total_price_after_discount
    
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

 

def update_orderitem_status(request, orderitem_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    try:
        order_item = get_object_or_404(OrderItem, orderitem_id=orderitem_id)
        order = order_item.order
        new_status = request.POST.get('status')
        total_price = Decimal(request.POST.get('total_price', '0'))
       
        cupon_discount = Decimal(request.POST.get('cupon_discount', '0'))
      
        subtotal_price = Decimal(request.POST.get('subtotal_price', '0'))
       
        return_reason = request.POST.get('return_reason', '')

        totalprice = total_price + cupon_discount
       

        if not new_status:
            return JsonResponse({'error': 'Status is required'}, status=400)
         
        def update_stock_and_wallet(amount):
            product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
            product_size.stock += order_item.quantity
            product_size.save()

            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            
            amount_to_add = subtotal_price - cupon_discount if order.coupon_used else subtotal_price
            
            if wallet.add_funds(amount_to_add):
                transaction_id = str(uuid.uuid4().hex[:8])
                Transaction.objects.create(
                    user=order.user,
                    transaction_id=transaction_id,
                    amount=amount,
                    status='Completed',
                    transaction_type='Credit'
                )
                return True
            return False

        with transaction.atomic():
            
            updated_total_price = total_price
            if new_status == "Cancelled":
                updated_total_price = totalprice - subtotal_price
        
                order_items = OrderItem.objects.filter(order=order)   

 
                if order.payment_status not in ["Pending", "Failure"]:
                    if totalprice - subtotal_price >= 1000:
                        if update_stock_and_wallet(subtotal_price):
                            messages.success(request, f"Order item cancelled and ${subtotal_price} added to your wallet!")
                        else:
                            return JsonResponse({'error': 'Failed to add funds to wallet'}, status=500)
                    else:
                         
                        # adjusted_amount = subtotal_price - cupon_discount
                        if order.coupon_used:
                        
                               adjusted_amount = subtotal_price
                        else:
                     
                              adjusted_amount = subtotal_price - cupon_discount
                       
                        if update_stock_and_wallet(adjusted_amount):
                            if not order.coupon_used:
                                order.coupon_used = True
                                order.save()
                            messages.success(request, f"Order item cancelled and ${adjusted_amount} added to your wallet!")
                        else:
                            return JsonResponse({'error': 'Failed to add funds to wallet'}, status=500)
                else:
                   messages.error(request, "The order item cannot be cancelled as its status is either 'Pending' or 'Failure'.")        
            elif new_status == "Returned":
              
                product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
                product_size.stock += order_item.quantity
                product_size.save()
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
                    messages.success(request, f"Order item returned and ${order_item.price} credited to your wallet!")
                else:
                    return JsonResponse({'error': 'Failed to add funds to wallet for return'}, status=500) 
            order_item.status = new_status
            order_item.save()

        messages.success(request, 'Order item status updated successfully.')
       
        return redirect(reverse('order:order_with_order', kwargs={'order_id': order.order_id}) + f'?updated_total_price={updated_total_price}')

    except Exception as e:
        return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)

    
# @never_cache
# # @admin_required
# def update_return_orderitem_status(request, orderitem_id):
#     if request.method == 'POST':
#         try:
#             order_item = get_object_or_404(OrderItem, orderitem_id=orderitem_id)
#             new_status = request.POST.get('status')
#             return_reason = request.POST.get('return_reason', '')   
#             if not new_status:
#                 return JsonResponse({'error': 'Status is required'}, status=400)
#             if new_status == "Approve Returned":
#                 product_size = get_object_or_404(ProductSize, product=order_item.product, size=order_item.size)
#                 product_size.stock += order_item.quantity
#                 product_size.save()
#                 order_item.return_reason = return_reason
#                 order_item.save()
#             order_item.status = new_status
#             order_item.save()
#             response = JsonResponse({'message': 'Order item return request updated successfully!', 'new_status': new_status}, status=200)
#             return response
#         except Exception as e:
#             return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)
#     else:
#         return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    
