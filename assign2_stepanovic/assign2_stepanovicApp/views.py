# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import auth
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.views import View
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from datetime import datetime, timezone
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from assign2_stepanovicApp.models import Auction
from assign2_stepanovicApp.forms import createAuction, confirmAuction, currencyExchangeRate, fetchRates, MyUserForm
from assign2_stepanovicApp.pyoxr import OXRClient

def auction(request):
    auctions = Auction.objects.order_by('-title')
    form = currencyExchangeRate()
    return render(request, "auctions.html",{'auctions':auctions, 'form':form})

@method_decorator(login_required, name="dispatch")
class CreateAuctionView(View):
    def get(self, request):
        form = createAuction()
        return render(request,'createauction.html', {'form' : form})

    def post(self, request):
        def dateValid(deadline):
            #deadline = datetime.strptime(date_string, "%d-%m-%Y")
            d = datetime.now(timezone.utc)
            diff = deadline - d
            if diff.days < 3:
                return False
            return True
        form = createAuction(request.POST)
        if form.is_valid():
            seller_id = request.user.id
            print("Sell", seller_id)
            cd = form.cleaned_data
            deadline = cd['deadline']
            minimum_price = cd['minimum_price']
            if not dateValid(deadline):
                messages.add_message(request, messages.ERROR, "Not valid deadline. The minimum duration of an auction is 72 hours from the moment it is created. ")
                return render(request, 'createauction.html', {'form': form, })
            if minimum_price <= 0:
                messages.add_message(request, messages.ERROR, "Not valid minimum price. The minimum price must be positive. ")
                return render(request, 'createauction.html', {'form': form, })
            if dateValid(deadline):
                title = cd['title']
                description = cd['description']
                form = confirmAuction()
                print(deadline)
                print(deadline.strftime('%d-%m-%Y %H:%M:%S'))
                deadline = deadline.strftime("%d-%m-%Y-%H:%M:%S")
                return render(request,'confirmauction.html', {'form' : form, 'seller_id': seller_id, 'title': title, 'description': description, 'minimum_price': minimum_price, 'deadline': deadline})
        else:
            messages.add_message(request, messages.ERROR, "Not valid data")
            return render(request,'createauction.html', {'form' : form, })

def saveauction(request):
    option = request.POST.get('option', '')
    if option == 'Yes':
        seller_id = request.POST.get('seller_id', '')
        print("Sell", seller_id)
        user = User.objects.get(id=seller_id)
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        minimum_price = request.POST.get('minimum_price', '')
        date_str = request.POST.get('deadline', '')
        print(date_str)
        auction = Auction(seller_id=seller_id, title = title, description = description, minimum_price = minimum_price, deadline = datetime.strptime(date_str, '%d-%m-%Y-%H:%M:%S'))
        auction.save()
        messages.add_message(request, messages.INFO, "New auction has been created")
        current_site = get_current_site(request)
        message = render_to_string('confirmemail.html', {
            'user': user,
            'auction': auction,
            'domain': current_site.domain,
        })

        send_mail(
            #'Your auction',
            'Your auction has been created.',
            message,
            'stepanovic2002@yahoo.com',
            [user.email],
            fail_silently=False,
        )
        return HttpResponseRedirect('/auction/')
    else:
        return HttpResponseRedirect('/auction/')

def showauction(request, id):
    auction = get_object_or_404(Auction, id=id)
#    if request.method == 'POST':
    form = currencyExchangeRate()
    rates = fetchRates()
    option = request.GET.get('option', '')
    if option in rates.keys():
        exchangeRate = rates[option]/rates["EUR"]
        form.fields["option"].initial = option
    else:
        exchangeRate = 1
        form.fields["option"].initial = "EUR"
    auction.minimum_price = auction.minimum_price * exchangeRate
    return render(request,"auctions.html",
        {'auctions' : [auction], 'form': form, 'id':id})


def searchauction(request, option):
    form = currencyExchangeRate()
    #if request.method=="POST":
    title = request.GET.get('title', '')
    auctions = Auction.objects.filter(title = title)
    rates = fetchRates()
    #option = request.GET.get('option', '')
    if option in rates.keys():
        exchangeRate = rates[option]/rates["EUR"]
        form.fields["option"].initial = option
    else:
        exchangeRate = 1
        form.fields["option"].initial = "EUR"
    for auction in auctions:
        auction.minimum_price = auction.minimum_price * exchangeRate
    #else:
        #auctions = Auction.objects.all()
        #title=''
    return render(request, "auctions.html",
                  {'auctions': auctions, 'title': title, 'form': form, 'option': option})

def changecurrency(request, title):
    id = request.GET.get('id', '')
    if id != '':
        auctions = Auction.objects.filter(id=id)
    elif title != '':
        auctions = Auction.objects.filter(title = title)
    else:
        auctions = Auction.objects.order_by('-title')
    form = currencyExchangeRate()
    rates = fetchRates()
    option = request.GET.get('option', '')
    if option in rates.keys():
        exchangeRate = rates[option]/rates["EUR"]
        form.fields["option"].initial = option
    else:
        exchangeRate = 1
        form.fields["option"].initial = "EUR"
    for auction in auctions:
        auction.minimum_price = auction.minimum_price * exchangeRate
    return render(request, "auctions.html",{'auctions':auctions, 'form':form, 'option':option, 'title':title, 'id':id})

def editauction(request, id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login/?next=%s' % request.path)
    auction = get_object_or_404(Auction, id=id)
    if request.user == auction.seller and auction.state == "Active":
        return render(request,"editauction.html", {'auction' : auction})
    elif auction.state != "Active":
        messages.add_message(request, messages.INFO, "Auction is not active")
        return HttpResponseRedirect(reverse("home"))
    else:
        messages.add_message(request, messages.INFO, "Only the seller can change the description of an auction")
        return HttpResponseRedirect(reverse("home"))

def updateauction(request, id):
    auctions = Auction.objects.filter(id= id)
    if len(auctions) > 0:
        auction = auctions[0]
    else:
        messages.add_message(request, messages.INFO, "Invalid auction id")
        return HttpResponseRedirect(reverse("home"))

    if request.method=="POST":
        description = request.POST["description"].strip()
        auction.description = description
        auction.save()
        messages.add_message(request, messages.INFO, "Auction description updated")

    return HttpResponseRedirect(reverse("home"))

def register (request):
    if request.method == 'POST':
        form = MyUserForm(request.POST)
        if form.is_valid():
            new_user = form.save()

            messages.add_message(request, messages.INFO, "New User is created. Please Login")

            return HttpResponseRedirect(reverse("home"))
        else:
            form = MyUserForm(request.POST)
    else:
        form =MyUserForm()

    return render(request,"registration.html", {'form': form})


def login_view (request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        nextTo = request.GET.get('next', reverse("home"))
        user = auth.authenticate(username=username, password=password)

        if user is not None and user.is_active:
            auth.login(request,user)
            print ("Password ", user.password)
            return HttpResponseRedirect(nextTo)

    return render(request,"login.html")

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, "Logged out")
    return HttpResponseRedirect(reverse("home"))

def edituser(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login/?next=%s' % request.path)
    else:
        form = MyUserForm()
        form.fields["username"].initial = request.user.username
        form.fields["username"].widget.attrs['readonly']  = True
        form.fields["username"].help_text = ""
        form.fields["email"].initial = request.user.email
        form.fields["password1"].label = "New password"
        form.fields["password2"].label = "New password confirmation"
        return render(request,"editaccount.html",{'form':form})

def updateuser(request):
    if request.method == 'POST':
        form = MyUserForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()
            messages.add_message(request, messages.INFO, "Your account was changed.  Please Login.")
        else:
            messages.add_message(request, messages.INFO, "Your new account information is not valid. Please, try again.")
    else:
        messages.add_message(request, messages.INFO, "Please, try again.")
    return HttpResponseRedirect(reverse("home"))
