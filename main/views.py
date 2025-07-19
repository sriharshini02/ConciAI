# main/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
import json
from datetime import timedelta, date
from django.db.models import Q # Import Q for complex queries

# Import ALL your models and forms here
from .models import Hotel, UserProfile, GuestRoomAssignment, Room, GuestRequest
from .forms import GuestRoomAssignmentForm

# --- Consolidated Staff Dashboard View ---

@login_required
def staff_dashboard(request, main_tab='home', sub_tab=None):
    """
    Renders the staff dashboard, handling different tabs (home, requests, guest_management)
    and sub-tabs for requests (active, archive, all).
    """
    # print(f"\n--- Entering staff_dashboard for user: {request.user.username} ---")
    # print(f"Is Authenticated: {request.user.is_authenticated}")

    user_hotel = None
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
        # print(f"UserProfile exists. Hotel linked: {user_hotel.name if user_hotel else 'None'}")
    except UserProfile.DoesNotExist:
        # print("UserProfile.DoesNotExist: UserProfile does not exist for this user.")
        logout(request)
        # print("Redirecting to login due to missing UserProfile.")
        return redirect('login')
    except AttributeError:
        # print("AttributeError: 'User' object has no attribute 'profile'.")
        logout(request)
        # print("Redirecting to login due to missing 'profile' attribute.")
        return redirect('login')

    if not user_hotel:
        # print("User profile exists, but no Hotel is linked to the profile.")
        logout(request)
        # print("Redirecting to login due to missing Hotel association.")
        return redirect('login')

    # print("User is authenticated and has a linked hotel. Proceeding to render dashboard.")

    context = {
        'page_title': 'Staff Dashboard', # Default title
        'current_main_tab': main_tab,
        'current_sub_tab': sub_tab,
    }

    # Common data for all tabs (e.g., room counts)
    today = timezone.localdate()
    now = timezone.localtime(timezone.now())
    total_rooms = user_hotel.total_rooms
    
    # Occupied rooms (guests currently checked in and status is 'checked_in')
    occupied_rooms = GuestRoomAssignment.objects.filter(
        hotel=user_hotel,
        check_in_time__lte=now,
        check_out_time__gte=now,
        status='checked_in'
    ).count()

    # Reserved rooms (future bookings, not yet checked in, status is 'confirmed')
    reserved_rooms = GuestRoomAssignment.objects.filter(
        hotel=user_hotel,
        check_in_time__date__gt=today,
        status='confirmed'
    ).count()

    # Dynamic Not Ready rooms count from Room model
    not_ready_rooms = Room.objects.filter(
        hotel=user_hotel,
        status__in=['cleaning', 'maintenance', 'out_of_service']
    ).count()

    available_rooms = total_rooms - occupied_rooms - reserved_rooms - not_ready_rooms
    if available_rooms < 0:
        available_rooms = 0

    context.update({
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'reserved_rooms': reserved_rooms,
        'available_rooms': available_rooms,
        'not_ready_rooms': not_ready_rooms,
    })

    if main_tab == 'home':
        context['page_title'] = 'Dashboard Overview'

        # New Bookings (GuestRoomAssignments created today, regardless of initial status)
        new_bookings_count = GuestRoomAssignment.objects.filter(
            hotel=user_hotel,
            created_at__date=today
        ).count()

        # Check-ins Today (GuestRoomAssignments with check_in_time today and status 'checked_in')
        check_ins_today_count = GuestRoomAssignment.objects.filter(
            hotel=user_hotel,
            check_in_time__date=today,
            status='checked_in'
        ).count()

        # Check-outs Today (GuestRoomAssignment.objects with check_out_time today and status 'checked_out')
        check_outs_today_count = GuestRoomAssignment.objects.filter(
            hotel=user_hotel,
            check_out_time__date=today,
            status='checked_out'
        ).count()

        # Total Requests (all GuestRequest for the hotel)
        total_requests_count = GuestRequest.objects.filter(hotel=user_hotel).count()

        context.update({
            'new_bookings_count': new_bookings_count,
            'check_ins_today_count': check_ins_today_count,
            'check_outs_today_count': check_outs_today_count,
            'total_requests_count': total_requests_count,
        })

        # --- Dynamic D3 Chart Data for Reservations (Last 7 Days) ---
        reservations_chart_data = []
        for i in range(7):
            chart_date = today - timedelta(days=6 - i)
            
            booked_count = GuestRoomAssignment.objects.filter(
                Q(created_at__date=chart_date) | Q(check_in_time__date=chart_date),
                hotel=user_hotel,
                status__in=['confirmed', 'checked_in']
            ).count()

            cancelled_count = GuestRoomAssignment.objects.filter(
                hotel=user_hotel,
                created_at__date=chart_date,
                status='cancelled'
            ).count()
            
            reservations_chart_data.append({
                "date": chart_date.strftime("%b %d"),
                "booked": booked_count,
                "cancelled": cancelled_count
            })
        context['reservations_chart_data'] = json.dumps(reservations_chart_data)

        # Booking by Platform Chart Data (Still hardcoded as 'platform' field is not in model)
        booking_platform_data = json.dumps([
            {"platform": "Direct Booking", "value": 61},
            {"platform": "Booking.com", "value": 12},
            {"platform": "Agoda", "value": 11},
            {"platform": "Airbnb", "value": 9},
            {"platform": "Hotels.com", "value": 5},
            {"platform": "Others", "value": 2}
        ])
        context['booking_platform_data'] = booking_platform_data

    elif main_tab == 'requests':
        context['page_title'] = 'Guest Requests'
        requests_for_hotel = GuestRequest.objects.filter(hotel=user_hotel)

        if sub_tab == 'active':
            requests_for_hotel = requests_for_hotel.exclude(status__in=['completed', 'cancelled'])
        elif sub_tab == 'archive':
            requests_for_hotel = requests_for_hotel.filter(status__in=['completed', 'cancelled'])
        elif sub_tab == 'all':
            pass

        requests_for_hotel = requests_for_hotel.order_by('-timestamp')

        requests_with_details = []
        for req in requests_for_hotel:
            assignment = GuestRoomAssignment.objects.filter(hotel=user_hotel, room_number=req.room_number).first()
            requests_with_details.append({
                'request': req,
                'assignment': assignment,
            })
        context['requests_with_details'] = requests_with_details

    elif main_tab == 'guest_management':
        context['page_title'] = 'Guest Management'
        
        # Initialize an empty form for GET requests or if POST fails validation
        form = GuestRoomAssignmentForm(hotel=user_hotel) 

        # Start with all assignments for the user's hotel
        all_assignments = GuestRoomAssignment.objects.filter(hotel=user_hotel)

        # --- Apply Filters ---
        filter_params = {}

        room_number = request.GET.get('room_number')
        if room_number:
            all_assignments = all_assignments.filter(room_number__icontains=room_number)
            filter_params['room_number'] = room_number

        guest_names = request.GET.get('guest_names')
        if guest_names:
            all_assignments = all_assignments.filter(guest_names__icontains=guest_names)
            filter_params['guest_names'] = guest_names

        status = request.GET.get('status')
        if status:
            all_assignments = all_assignments.filter(status=status)
            filter_params['status'] = status

        check_in_date_from = request.GET.get('check_in_date_from')
        if check_in_date_from:
            try:
                # Convert to date object for filtering
                from_date = timezone.datetime.strptime(check_in_date_from, '%Y-%m-%d').date()
                all_assignments = all_assignments.filter(check_in_time__date__gte=from_date)
                filter_params['check_in_date_from'] = check_in_date_from
            except ValueError:
                pass # Handle invalid date format if necessary

        check_in_date_to = request.GET.get('check_in_date_to')
        if check_in_date_to:
            try:
                to_date = timezone.datetime.strptime(check_in_date_to, '%Y-%m-%d').date()
                all_assignments = all_assignments.filter(check_in_time__date__lte=to_date)
                filter_params['check_in_date_to'] = check_in_date_to
            except ValueError:
                pass

        check_out_date_from = request.GET.get('check_out_date_from')
        if check_out_date_from:
            try:
                from_date = timezone.datetime.strptime(check_out_date_from, '%Y-%m-%d').date()
                all_assignments = all_assignments.filter(check_out_time__date__gte=from_date)
                filter_params['check_out_date_from'] = check_out_date_from
            except ValueError:
                pass

        check_out_date_to = request.GET.get('check_out_date_to')
        if check_out_date_to:
            try:
                to_date = timezone.datetime.strptime(check_out_date_to, '%Y-%m-%d').date()
                all_assignments = all_assignments.filter(check_out_time__date__lte=to_date)
                filter_params['check_out_date_to'] = check_out_date_to
            except ValueError:
                pass

        # Order the filtered results
        all_assignments = all_assignments.order_by('-check_in_time')

        context.update({
            'form': form, # Pass the form for the add/edit modal
            'all_assignments': all_assignments, # Pass the filtered assignments
            'assignment_status_choices': GuestRoomAssignment.STATUS_CHOICES, # Pass choices for status filter
            'filter_params': filter_params, # Pass current filter values to re-populate form fields
        })

        if request.method == 'POST':
            # This block handles the form submission for adding/editing assignments
            assignment_id = request.POST.get('assignment_id')
            
            if assignment_id:
                assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=user_hotel)
                form = GuestRoomAssignmentForm(request.POST, instance=assignment, hotel=user_hotel)
            else:
                form = GuestRoomAssignmentForm(request.POST, hotel=user_hotel) 

            if form.is_valid():
                form.save()
                return JsonResponse({'success': True, 'message': 'Guest assignment saved successfully.'})
            else:
                return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
            
    return render(request, 'main/staff_dashboard.html', context)


# --- Staff Dashboard API Endpoints (remain the same) ---

@login_required
@require_GET
def check_for_new_requests(request):
    """
    API endpoint to check for new pending requests for the notification bell.
    Matches URL: /api/check_new_requests/
    """
    # Safely access user_hotel via UserProfile for API endpoint
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'User profile not linked.'}, status=403)

    last_check_str = request.GET.get('last_check')

    new_requests_exist = False
    new_requests_count = 0

    if last_check_str:
        try:
            if last_check_str.endswith('Z'):
                last_check_str = last_check_str.replace('Z', '+00:00')
            last_check_timestamp = timezone.datetime.fromisoformat(last_check_str)
            
            if timezone.is_naive(last_check_timestamp):
                last_check_timestamp = timezone.make_aware(last_check_timestamp, timezone.get_current_timezone())

            new_requests_count = GuestRequest.objects.filter(
                hotel=user_hotel,
                status='pending',
                timestamp__gt=last_check_timestamp
            ).count()

            if new_requests_count > 0:
                new_requests_exist = True

        except ValueError:
            print(f"Warning: Invalid last_check timestamp format: {last_check_str}")
            pass

    return JsonResponse({
        'success': True,
        'new_requests_exist': new_requests_exist,
        'new_requests_count': new_requests_count,
        'current_timestamp': timezone.localtime(timezone.now()).isoformat(),
    })

@login_required
@require_POST
def update_staff_notes(request, request_id):
    """
    API endpoint to update staff notes for a specific request.
    Matches URL: /request/<int:request_id>/update_notes/
    """
    try:
        req = get_object_or_404(GuestRequest, id=request_id, hotel=request.user.profile.hotel)
        notes = request.POST.get('notes', '')
        req.staff_notes = notes
        req.save()
        return JsonResponse({'success': True, 'message': 'Notes saved successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def update_request_status(request, request_id):
    """
    API endpoint to update the status of a specific request.
    Matches URL: /request/<int:request_id>/update_status/
    """
    try:
        req = get_object_or_404(GuestRequest, id=request_id, hotel=request.user.profile.hotel)
        new_status = request.POST.get('new_status')
        if new_status in dict(req.STATUS_CHOICES):
            req.status = new_status
            req.save()
            return redirect('main:guest_requests_dashboard') 
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status provided.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_GET
def get_request_details(request, request_id):
    """
    API endpoint to fetch detailed information about a request for a modal.
    Matches URL: /api/requests/<int:request_id>/details/
    """
    try:
        req = get_object_or_404(GuestRequest, id=request_id, hotel=request.user.profile.hotel)
        
        assignment = GuestRoomAssignment.objects.filter(hotel=request.user.profile.hotel, room_number=req.room_number).first()
        guest_names = assignment.guest_names if assignment else "N/A"

        ai_entities_data = {}
        if req.ai_entities:
            try:
                ai_entities_data = json.loads(req.ai_entities)
            except json.JSONDecodeError:
                ai_entities_data = {}

        chat_history_data = []
        if req.chat_history:
            try:
                chat_history_data = json.loads(req.chat_history)
            except json.JSONDecodeError:
                chat_history_data = []

        details = {
            'success': True,
            'room_number': req.room_number,
            'guest_names': guest_names,
            'raw_text': req.raw_text,
            'ai_intent': req.ai_intent or 'N/A',
            'ai_entities': ai_entities_data,
            'conci_response_text': req.conci_response_text or 'No response yet.',
            'status': req.get_status_display(),
            'timestamp': req.timestamp.isoformat(),
            'staff_notes': req.staff_notes or 'No notes.',
            'chat_history': chat_history_data,
        }
        return JsonResponse(details)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def edit_guest_assignment(request, assignment_id):
    """
    API endpoint to handle editing of a guest assignment via AJAX.
    Matches URL: /api/assignments/<int:assignment_id>/edit/
    """
    # Safely access user_hotel via UserProfile
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'User profile not linked.'}, status=403)

    assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=user_hotel)
    
    mutable_post = request.POST.copy()

    check_in_date = mutable_post.get('check_in_date')
    check_in_time_input = mutable_post.get('check_in_time_input')
    if check_in_date and check_in_time_input:
        mutable_post['check_in_time'] = f"{check_in_date} {check_in_time_input}"
    
    check_out_date = mutable_post.get('check_out_date')
    check_out_time_input = mutable_post.get('check_out_time_input')
    if check_out_date and check_out_time_input:
        mutable_post['check_out_time'] = f"{check_out_date} {check_out_time_input}"

    # Pass hotel to the form when editing as well
    form = GuestRoomAssignmentForm(mutable_post, instance=assignment, hotel=user_hotel)
    
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Assignment updated successfully.'})
    else:
        return JsonResponse({'success': False, 'errors': json.dumps(form.errors)}, status=400)

@login_required
@require_POST
def delete_guest_assignment(request, assignment_id):
    """
    API endpoint to handle deletion of a guest assignment via AJAX.
    Matches URL: /api/assignments/<int:assignment_id>/delete/
    """
    # Safely access user_hotel via UserProfile
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'User profile not linked.'}, status=403)

    try:
        assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=user_hotel)
        assignment.delete()
        return JsonResponse({'success': True, 'message': 'Assignment deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# --- Guest Interface Views ---

def guest_interface(request, hotel_id, room_number):
    """
    Renders the guest-facing interface for a specific room in a hotel.
    Matches URL: /guest/<int:hotel_id>/<str:room_number>/
    """
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    current_assignment = GuestRoomAssignment.objects.filter(
        hotel=hotel,
        room_number=room_number,
        check_in_time__lte=timezone.localtime(timezone.now()),
        check_out_time__gte=timezone.localtime(timezone.now())
    ).first()

    latest_request = GuestRequest.objects.filter(
        hotel=hotel,
        room_number=room_number
    ).order_by('-timestamp').first()

    chat_history = []
    if latest_request and latest_request.chat_history:
        try:
            chat_history = json.loads(latest_request.chat_history)
        except json.JSONDecodeError:
            chat_history = []

    context = {
        'hotel': hotel,
        'room_number': room_number,
        'guest_names': current_assignment.guest_names if current_assignment else "Guest",
        'latest_request_id': latest_request.id if latest_request else None,
        'chat_history': json.dumps(chat_history),
    }
    return render(request, 'main/guest_interface.html', context)


# --- Guest Interface API Endpoints ---

@require_POST
def process_guest_command(request):
    """
    API endpoint to process a guest's command (new request).
    This simulates AI processing and Conci's response.
    Matches URL: /api/process_command/
    Expects hotel_id and room_number in the JSON body.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message')
        hotel_id = data.get('hotel_id') # Get from body
        room_number = data.get('room_number') # Get from body

        if not user_message or not hotel_id or not room_number:
            return JsonResponse({'success': False, 'error': 'Missing message, hotel_id, or room_number.'}, status=400)

        hotel = get_object_or_404(Hotel, id=hotel_id)

        # Always create a new GuestRequest for each command/message from the guest interface
        # The chat_history will be initialized for this new request.
        chat_history = []
        chat_history.append({"role": "user", "parts": [{"text": user_message}]})
        
        # Simulate AI processing and response for this new command
        ai_intent = "General Inquiry"
        ai_entities = {"query": user_message}
        conci_response = "Thank you for your request. We have received it and will get back to you shortly."
        chat_history.append({"role": "model", "parts": [{"text": conci_response}]})

        request_obj = GuestRequest.objects.create(
            hotel=hotel,
            room_number=room_number,
            raw_text=user_message,
            ai_intent=ai_intent,
            ai_entities=json.dumps(ai_entities),
            conci_response_text=conci_response,
            status='pending', # New requests start as 'pending'
            chat_history=json.dumps(chat_history)
        )
        
        return JsonResponse({
            'success': True,
            'conci_response': conci_response,
            'request_id': request_obj.id,
            'chat_history': chat_history, # Return the chat history for this specific new request
        })

    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON in request body.")
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def submit_draft_requests(request):
    """
    API endpoint for guest interface to submit a draft request (e.g., from a form).
    This now always creates a new request.
    Matches URL: /api/submit_draft_requests/
    Expects hotel_id and room_number in the JSON body.
    """
    try:
        data = json.loads(request.body)
        request_text = data.get('request_text') # This is the combined text from pending requests
        hotel_id = data.get('hotel_id')
        room_number = data.get('room_number')

        if not request_text or not hotel_id or not room_number:
            return JsonResponse({'success': False, 'error': 'Missing request_text, hotel_id, or room_number.'}, status=400)

        hotel = get_object_or_404(Hotel, id=hotel_id)

        # Always create a new GuestRequest for confirmed draft requests
        chat_history = []
        chat_history.append({"role": "user", "parts": [{"text": request_text}]})

        conci_ack = "Your request has been submitted. We will attend to it shortly."
        chat_history.append({"role": "model", "parts": [{"text": conci_ack}]})

        request_obj = GuestRequest.objects.create(
            hotel=hotel,
            room_number=room_number,
            raw_text=request_text,
            conci_response_text=conci_ack,
            status='pending', # New requests start as 'pending'
            chat_history=json.dumps(chat_history)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Request submitted successfully.',
            'request_id': request_obj.id,
            'chat_history': chat_history, # Return updated chat history
        })

    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON in request body.")
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
def check_for_new_updates(request, hotel_id, room_number):
    """
    API endpoint for the guest interface to check for new responses from Conci.
    Matches URL: /api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/
    """
    last_request_id = request.GET.get('last_request_id')
    
    hotel = get_object_or_404(Hotel, id=hotel_id)
    
    # Get the latest request for this room, regardless of status
    latest_request = GuestRequest.objects.filter(
        hotel=hotel,
        room_number=room_number
    ).order_by('-timestamp').first()

    new_messages = []
    has_new_updates = False
    updated_request_id = latest_request.id if latest_request else None

    if latest_request:
        # Check if the latest request in DB is different from what the guest has
        # This means either a new request was created, or an existing one was updated by staff.
        if str(latest_request.id) != str(last_request_id): # Ensure comparison is string to string
            has_new_updates = True
            if latest_request.chat_history:
                try:
                    new_messages = json.loads(latest_request.chat_history)
                except json.JSONDecodeError:
                    new_messages = []
            
    return JsonResponse({
        'has_new_updates': has_new_updates,
        'new_messages': new_messages,
        'updated_request_id': updated_request_id,
    })


def user_logout(request):
    logout(request)
    return redirect('login') # Assuming 'login' is the name of your login URL
