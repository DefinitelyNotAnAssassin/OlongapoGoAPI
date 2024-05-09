from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import auth, messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.mail import send_mail

from datetime import datetime

from accounts.utils import get_checkbox_input

from .utils import user_role_in_ride, str_to_datetime
from .models import Ride

@csrf_exempt
def rides(request):
    """List all rides"""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    
    user = get_object_or_404(User, id=request.user.id)
    rides_as_owner = user.rides_as_owner.all().order_by(
        'id').filter(~Q(ride_status='complete'))
    rides_as_driver = user.rides_as_driver.all().order_by(
        'id').filter(~Q(ride_status='complete'))
    rides_as_sharer = user.rides_as_sharer.all().order_by(
        'id').filter(~Q(ride_status='complete'))

    context = {
        'rides_as_owner': rides_as_owner,
        'rides_as_driver': rides_as_driver,
        'rides_as_sharer': rides_as_sharer,
    }

    return render(request, 'rides/rides.html', context)

@csrf_exempt
def ride(request, ride_id):
    """Detail page for ride with ride_id"""
    # Authentication
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    user = get_object_or_404(User, id=request.user.id)
    ride = get_object_or_404(Ride, id=ride_id)
    
    user_role = user_role_in_ride(user, ride)
    if user_role == 'other':
        return HttpResponse(status=404)
    else:
        context = {
            'ride': ride,
        }
        return render(request, 'rides/ride.html', context)
        
@csrf_exempt
def search(request):
    """Return search results"""
    
    # GET
    if request.method == 'GET':
        return render(request, 'rides/search.html')
    # POST
    if request.method == 'POST':
        search_as = request.POST.get('search_as')
        if search_as not in ['driver', 'sharer']:
            return HttpResponse(status=404)
        if search_as == 'driver':
            
            rides = Ride.objects.order_by('-id').filter(
                Q(ride_status='open'),
               
            )

    
            
            context = {
                'rides': rides,
                'search_as_driver': True,
            }
            return JsonResponse({'rides': list(rides.values())}, safe=False)
        
        
          
@csrf_exempt
def create(request):
    """Create a ride(as owner)"""
    # Authentication
   
    # GET
    if request.method == 'GET':
        return render(request, 'rides/create.html')
    # POST
    if request.method == 'POST':
        user = get_object_or_404(User, id=request.POST['currentUser'])
        
        destination = request.POST['destination']
       
        required_arrival_time =datetime.strptime(request.POST['arrival_time'], "%m/%d/%YT%H:%M")

        passenger_number_from_owner = request.POST['number_of_passengers']
        requested_vehicle_type = request.POST['vehicle_type']
        special_request = request.POST['special_request']
        
        # create object
        Ride.objects.create(
            owner=user,
            destination=destination, required_arrival_time=required_arrival_time,
            passenger_number_from_owner=passenger_number_from_owner,
            passenger_number_in_total=passenger_number_from_owner,
            can_be_shared=False, 
            requested_vehicle_type=requested_vehicle_type, 
            special_request=special_request,
        )
        # send message & return
        messages.success(request, 'You have successfully made a request.')
        return HttpResponse(status=200)
    

def edit(request, ride_id):
    """Edit a ride"""
    # Authentication
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    # Identify User's role
    user = get_object_or_404(User, id=request.user.id)
    ride = get_object_or_404(Ride, id=ride_id)
    user_role = user_role_in_ride(user, ride)
    # GET: Display ride information
    if request.method == 'GET':
        context = {
            'ride': ride,
            'edit_as': user_role,
        }
        return render(request, 'rides/edit.html', context)
    # POST: Update ride information(for owner only), driver and sharer user different methods below
    if request.method == 'POST' and user_role == 'owner' and ride.ride_status == 'open':
        # get form inputs
        destination = request.POST['destination']
        required_arrival_time = str_to_datetime(
            request.POST['arrival_time']
        )
        passenger_number_from_owner = int(request.POST['number_of_passengers'])
        requested_vehicle_type = request.POST['vehicle_type']
        special_request = request.POST['special_request']
        can_be_shared = get_checkbox_input('can_be_shared', request)
        # Update ride information
        ride.destination = destination
        ride.required_arrival_time = required_arrival_time
        ride.can_be_shared = can_be_shared
        ride.requested_vehicle_type = requested_vehicle_type
        ride.special_request = special_request

        old_passenger_number_from_owner = ride.passenger_number_from_owner # pay special attention
        ride.passenger_number_from_owner = passenger_number_from_owner  # pay special attention
        ride.passenger_number_in_total += (passenger_number_from_owner - old_passenger_number_from_owner)

        ride.save()
        return redirect('rides')


def confirm(request, ride_id):
    """Confirm the ride with ride_id"""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if request.method != 'POST':
        return HttpResponse(status=404)

    user = get_object_or_404(User, id=request.user.id)
    ride = get_object_or_404(Ride, id=ride_id)
    if not user.driverProfile.is_driver:
        return HttpResponse(status=404)
    if ride.ride_status != 'open':
        return HttpResponse(status=404)
    
    ride.driver = user
    ride.ride_status = 'confirm'
    ride.save()
    
    email_list = [ride.owner.email]
    for sharer in ride.sharers.all():
        email_list.append(sharer.email)
    send_mail(
      'Ride Confirmed',
      'Your ride has been confirmed by driver' + ride.driver.driverProfile.real_name,
      'rover_admin@rover.co',
      email_list,
      fail_silently=True,
    )
    messages.success(request, 'You have successfully confirmed the ride.')
    return redirect('rides')


def complete(request, ride_id):
    """Complete the ride with ride_id"""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if request.method != 'POST':
        return HttpResponse(status=404)
    
    user = get_object_or_404(User, id=request.user.id)
    ride = get_object_or_404(Ride, id=ride_id)
    user_role = user_role_in_ride(user, ride)
    if not user.driverProfile.is_driver:
        return HttpResponse(status=404)
    if user_role != 'driver':
        return HttpResponse(status=404)
    
    ride.ride_status = 'complete'
    ride.save()
    messages.success(request, 'You have successfully completed the ride.')
    return redirect('rides')


def share(request, ride_id):
    """Share the ride with ride_id"""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if request.method != 'POST':
        return HttpResponse(status=404)

    user = get_object_or_404(User, id=request.user.id)
    ride = get_object_or_404(Ride, id=ride_id)
    if not ride.can_be_shared:
        return HttpResponse(status=404)

    new_number_of_passengers = int(request.POST['number_of_passengers'])
    if user not in ride.sharers.all():
        ride.sharers.add(user)

    # bug fix: object is null when init, object.get is not supported
    if not ride.sharer_id_and_passenger_number_pair:
        ride.sharer_id_and_passenger_number_pair = {}
    # bug fix: dictionary key should always be string
    record = ride.sharer_id_and_passenger_number_pair.get(str(user.id))
    old_number_of_passengers = record['number_of_passengers'] if record else 0
    ride.passenger_number_in_total += (
        new_number_of_passengers - old_number_of_passengers
    )
    ride.sharer_id_and_passenger_number_pair[user.id] = {
        'username': user.username,
        'number_of_passengers': new_number_of_passengers
    }
    ride.save()
    messages.success(request, 'You have joined the ride.')
    return redirect('rides')


@csrf_exempt
def getRides(request): 
    if request.method == "POST": 
        data = request.POST 
        currentUser = data.get('currentUser')
        user = get_object_or_404(User, id=currentUser)
        is_driver = user.driverProfile.is_driver
        
        if is_driver: 
            driverRides = Ride.objects.filter(driver=user).order_by('-id').values(
                'id',
                'owner__first_name',
                'owner__last_name',
                'driver__first_name',
                'driver__last_name',
                'destination',
                'required_arrival_time',
                'passenger_number_from_owner',
                'passenger_number_in_total',
                'ride_status',
                'requested_vehicle_type',
                'special_request',
                
            )
            rideList = []
            for ride in driverRides:
                rideMap = {}
                rideMap["id"] = ride["id"]
                rideMap["owner_id"] = ride["owner__first_name"] + " " + ride["owner__last_name"]
                rideMap["driver_id"] = ride["driver__first_name"] + " " + ride["driver__last_name"]
                rideMap["destination"] = ride["destination"]
                rideMap["required_arrival_time"] = ride["required_arrival_time"]
                rideMap["passenger_number_from_owner"] = ride["passenger_number_from_owner"]
                rideMap["passenger_number_in_total"] = ride["passenger_number_in_total"]
                rideMap["ride_status"] = ride["ride_status"]
                rideMap["requested_vehicle_type"] = ride["requested_vehicle_type"]
                rideMap["special_request"] = ride["special_request"]
                rideList.append(rideMap)
            return JsonResponse({'driver_rides': rideList}, safe=False)
        elif not is_driver: 
            userRides = Ride.objects.filter(owner=user).order_by('-id').values('owner__first_name', 'owner__last_name', 'owner__username', 'destination', 'required_arrival_time', 'passenger_number_from_owner', 'passenger_number_in_total', 'ride_status', 'requested_vehicle_type', 'special_request', 'can_be_shared', 'sharers__first_name', 'sharers__last_name',  'id', 'driver_id', 'driver__first_name', 'driver__last_name', 'driver__username')
            return JsonResponse({'message': 'Login successful', 'user_id': user.id, 'first_name': user.first_name, 'last_name' : user.last_name, 'is_driver': is_driver, 'user_rides': list(userRides) }, safe = False)

