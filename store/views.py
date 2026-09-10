from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from .models import CartItem, Category, Order, OrderItem, Product


def product_list(request):
    products = Product.objects.select_related('category').all()
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    if query:
        products = products.filter(name__icontains=query)
    if category:
        products = products.filter(category__slug=category)
    return render(request, 'store/product_list.html', {'products': products, 'categories': Category.objects.all()})


def product_detail(request, slug):
    return render(request, 'store/product_detail.html', {'product': get_object_or_404(Product, slug=slug)})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    item, _ = CartItem.objects.get_or_create(user=request.user, product=product)
    if request.method == 'POST':
        quantity = max(1, int(request.POST.get('quantity', 1)))
        item.quantity = min(quantity, product.stock) if product.stock else quantity
        item.save()
    return redirect('cart')


@login_required
def cart(request):
    items = CartItem.objects.select_related('product').filter(user=request.user)
    total = sum((item.subtotal for item in items), Decimal('0.00'))
    return render(request, 'store/cart.html', {'items': items, 'total': total})


@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(pk=item_id, user=request.user).delete()
    return redirect('cart')


@login_required
def checkout(request):
    items = list(CartItem.objects.select_related('product').filter(user=request.user))
    if not items:
        return redirect('cart')
    with transaction.atomic():
        order = Order.objects.create(user=request.user)
        total = Decimal('0.00')
        for item in items:
            if item.product.stock < item.quantity:
                return render(request, 'store/cart.html', {'items': items, 'total': total, 'error': f'Not enough stock for {item.product.name}.'})
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
            item.product.stock -= item.quantity
            item.product.save(update_fields=['stock'])
            total += item.subtotal
        order.total = total
        order.save(update_fields=['total'])
        CartItem.objects.filter(user=request.user).delete()
    return redirect('orders')


@login_required
def orders(request):
    return render(request, 'store/orders.html', {'orders': request.user.orders.prefetch_related('items__product').all()})
