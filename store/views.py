from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse
from django.views import View
import json
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder

def store(request):
	data = cartData(request)

	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	products = Product.objects.all()
	context = {'products':products, 'cartItems':cartItems}
	return render(request, 'store/store.html', context)


def cart(request):
	if request.session.get('customer'):
		customer = Customer(id=request.session.get('customer'))
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
		items = order.orderitem_set.all()
		cartItems = order.get_cart_items
	else:
		#Create empty cart for now for non-logged in user
		items = []
		order = []
	context = {'items': items, 'order': order, 'cartItems': cartItems}
	return render(request, 'store/cart.html', context)

	# data = cartData(request)

	# cartItems = data['cartItems']
	# order = data['order']
	# items = data['items']

	# context = {'items':items, 'order':order, 'cartItems':cartItems}
	# return render(request, 'store/cart.html', context)

def checkout(request):
	data = cartData(request)
	
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = Customer(id=request.session.get('customer'))
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)

	if request.session.get('customer'):
		customer = Customer(id=request.session.get('customer'))
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, data)

	total = float(data['form']['total'])
	order.transaction_id = transaction_id

	if total == order.get_cart_total:
		order.complete = True
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
		customer=customer,
		order=order,
		address=data['shipping']['address'],
		city=data['shipping']['city'],
		state=data['shipping']['state'],
		zipcode=data['shipping']['zipcode'],
		)

	return JsonResponse('Payment submitted..', safe=False)

class Login(View):
    return_url = None
  
    def get(self, request):
        Login.return_url = request.GET.get('return_url')
        return render(request, 'store/login.html')
  
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        customer = Customer.get_customer_by_email(email)
        error_message = None
        if customer:
            flag = check_password(password, customer.password)
            if flag:
                if Login.return_url:
                    return HttpResponseRedirect(Login.return_url)
                else:
                    request.session['customer'] = customer.id
                    Login.return_url = None
                    return redirect('/')
            else:
                error_message = 'Invalid password'
        else:
            error_message = 'User not found'
  
        print(email, password)
        return render(request, 'store/login.html', {'error': error_message})
  
  
def logout(request):
    request.session.clear()
    return redirect('login')
  
  
class Signup (View):
    def get(self, request):
        return render(request, 'store/signup.html')
  
    def post(self, request):
        postData = request.POST
        name = postData.get("name");
        email = postData.get('email')
        password = postData.get('password')
        # validation
        value = {
            'name': name,
            'email': email
        }
        error_message = None
  
        customer = Customer(name=name,
                            email=email,
                            password=password)
        error_message = self.validateCustomer(customer)
  
        if not error_message:
            print(name, email, password)
            customer.password = make_password(customer.password)
            request.session['customer'] = customer.id
            customer.register()
            return redirect('/')
        else:
            data = {
                'error': error_message,
                'values': value
            }
            return render(request, 'store/signup.html', data)
  
    def validateCustomer(self, customer):
        error_message = None
        if (not customer.name):
            error_message = "Please enter your name."
        elif len(customer.name) < 3:
            error_message = 'Name must be 3 characters long or more'
        elif len(customer.password) < 5:
            error_message = 'Password must be 5 char long'
        elif len(customer.email) < 5:
            error_message = 'Email must be 5 char long'
        elif customer.isExists():
            error_message = 'User with email address already exists'
        # saving
  
        return error_message