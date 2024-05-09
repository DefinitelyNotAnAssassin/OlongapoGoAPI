from django.shortcuts import render, redirect
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import DriverProfile
from rides.models import Ride
from .models import DriverProfile


from .utils import is_email, is_driver, get_driver_profile_by_request

@csrf_exempt
def register(request):
    if request.method == 'POST':
        first_name = request.POST['fname']
        last_name = request.POST['lname']
        email = request.POST['gmail']
        password = request.POST['password']
        username = request.POST['username']
        if is_email(email) is False:
            messages.error(request, 'Wrong formatted email address.')
            return redirect('register')
        
 
        else: # validation passed
            user = User.objects.create_user(
                username=username, email=email, 
                password=password, first_name=first_name, 
                last_name=last_name
            )
            user.save()
            messages.success(request, 'You are now registered and can login.')
            return JsonResponse({'message': 'You are now registered and can login.', 'currentUser' : user.pk}, safe = False)
    else:
        return render(request, 'accounts/register.html')

@csrf_exempt
def login(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('dashboard')
        else:
            return render(request, 'accounts/login.html')

    if request.method == 'POST':
        
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            is_driver = get_driver_profile_by_request(request).is_driver    
            if is_driver:
                driverRides = Ride.objects.filter(driver=user)
                
                
                
                driverRides = Ride.objects.filter(driver=user).values('owner__first_name', 'owner__last_name', 'owner__username', 'destination', 'required_arrival_time', 'passenger_number_from_owner', 'passenger_number_in_total', 'ride_status', 'requested_vehicle_type', 'special_request', 'can_be_shared', 'sharers__first_name', 'sharers__last_name', 'sharers__username', 'sharer_id_and_passenger_number_pair', 'id', 'driver_id', 'driver__first_name', 'driver__last_name', 'driver__username') 
                
                return JsonResponse({'message': 'Login successful', 'user_id': user.id, 'first_name': user.first_name, 'last_name' : user.last_name, 'is_driver': is_driver, 'driver_rides': list(driverRides) }, safe = False)
            else:
                userRides = Ride.objects.filter(owner=user) 
                userRides = Ride.objects.filter(owner=user).values('owner__first_name', 'owner__last_name', 'owner__username', 'destination', 'required_arrival_time', 'passenger_number_from_owner', 'passenger_number_in_total', 'ride_status', 'requested_vehicle_type', 'special_request', 'can_be_shared', 'sharers__first_name', 'sharers__last_name',  'id', 'driver_id', 'driver__first_name', 'driver__last_name', 'driver__username')
                return JsonResponse({'message': 'Login successful', 'user_id': user.id, 'first_name': user.first_name, 'last_name' : user.last_name, 'is_driver': is_driver, 'user_rides': list(userRides) }, safe = False)


        else:
            messages.error(request, 'Invalid credential')
            return JsonResponse({'message': 'Invalid credential'})


def logout(request):
    if request.method == 'POST':
        auth.logout(request)
        messages.success(request, 'You have successfully logged out.')
        return redirect('index')


def dashboard(request):
    # variable = $DriverProfile->all()  
    driverProfiles = DriverProfile.objects.filter(is_driver=True)
    
    
    
    return render(request, 'accounts/dashboard.html')


def driver_register(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if request.user.driverProfile.is_driver:
        messages.error(request, 'You are already a driver.')
        return redirect('dashboard')
    # Get
    if request.method == 'GET':
        return render(request, 'accounts/driver_register.html')
    # POST
    if request.method == 'POST':
        real_name = request.POST['real_name']
        vehicle_type = request.POST['vehicle_type']
        license_plate_number = request.POST['license_plate_number']
        maximum_passengers = int(request.POST['maximum_passengers'])
        special_vehicle_info = request.POST['special_vehicle_info']

        driver_profile = request.user.driverProfile
        
        driver_profile.real_name = real_name
        driver_profile.vehicle_type = vehicle_type
        driver_profile.license_plate_number = license_plate_number
        driver_profile.maximum_passengers = maximum_passengers
        driver_profile.special_vehicle_info = special_vehicle_info
        driver_profile.is_driver = True
        driver_profile.save()

        messages.success(request, 'Congratulate on being a driver.')
        return redirect('dashboard')


def driver_update_info(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.driverProfile.is_driver:
        messages.error(request, 'You are not a driver.')
        return redirect('dashboard')
    # GET
    if request.method == 'GET':
        context = {
            'driver_profile': request.user.driverProfile
        }
        return render(request, 'accounts/driver_update_info.html', context)
    # POST
    if request.method == 'POST':
        real_name = request.POST['real_name']
        vehicle_type = request.POST['vehicle_type']
        license_plate_number = request.POST['license_plate_number']
        maximum_passengers = int(request.POST['maximum_passengers'])
        special_vehicle_info = request.POST['special_vehicle_info']

        driver_profile = request.user.driverProfile

        driver_profile.real_name = real_name
        driver_profile.vehicle_type = vehicle_type
        driver_profile.license_plate_number = license_plate_number
        driver_profile.maximum_passengers = maximum_passengers
        driver_profile.special_vehicle_info = special_vehicle_info
        driver_profile.save()

        messages.success(request, 'Update driver\'s info successfully.')
        return redirect('dashboard')
