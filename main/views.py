# main/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
import json
from datetime import timedelta, date
from django.db.models import Q
import requests
from asgiref.sync import sync_to_async
import os
from dotenv import load_dotenv
from .models import Hotel, UserProfile, GuestRoomAssignment, Room, GuestRequest, Amenity
from .forms import AmenityForm, GuestRoomAssignmentForm

# Load environment variables from .env file
load_dotenv()

# --- Gemini API Configuration ---
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

async def call_gemini_api(prompt, available_amenities_data):
    """
    Calls the Gemini API to get intent, entities, and a response.
    Args:
        prompt (str): The user's message.
        available_amenities_data (list): A list of dictionaries, each with 'name' and 'price' of available amenities.
    Returns:
        dict: Parsed JSON response from Gemini, or an error structure.
    """
    # Explicit API key check
    if not GEMINI_API_KEY:
        print("Error: GOOGLE_API_KEY not set for Gemini API.")
        return {
            "intent": "general_inquiry",
            "entities": {"query": prompt},
            "conci_response": "I'm sorry, my AI capabilities are currently offline due to a missing API key. Please inform the staff."
        }

    chat_history = []
    
    # Provide context about available amenities to the AI, including price
    amenities_info_parts = []
    for amenity in available_amenities_data:
        amenities_info_parts.append(f"{amenity['name']} (${amenity['price']:.2f})")
    
    amenities_info = "Available amenities: " + ", ".join(amenities_info_parts) + "."
    if not amenities_info_parts:
        amenities_info = "No specific amenities are currently listed as available."

    # System instruction for the AI
    system_instruction_text = f"""
    You are an AI hotel concierge named Conci. Your primary goal is to assist guests with their requests.
    Analyze the guest's message to determine their intent and extract relevant entities.
    
    Here are the possible request types you can identify:
    - 'amenity_request': The guest is asking for a specific item that is an amenity (e.g., "water bottle", "fresh towels", "extra pillow").
    - 'maintenance': The guest is reporting a problem that requires maintenance (e.g., "AC not working", "leaky faucet", "light is broken").
    - 'housekeeping': The guest is requesting cleaning or supplies related to housekeeping (e.g., "clean my room", "more soap", "new bedding").
    - 'room_service': The guest is asking for food or drinks (e.g., "order breakfast", "bring coffee", "menu").
    - 'concierge': The guest is asking for information or assistance typically provided by a concierge (e.g., "taxi", "restaurant recommendation", "directions", "what to do").
    - 'general_inquiry': A general question or statement that doesn't fit other categories but requires a helpful response (e.g., "What time is checkout?", "Do you have Wi-Fi?").
    - 'casual_chat': A greeting, farewell, or simple conversational filler that doesn't require an action (e.g., "Hi", "Thank you", "How are you?").

    {amenities_info}

    When an 'amenity_request' is identified, also extract the 'amenity_name' (must exactly match one of the available amenities if possible) and 'quantity' (default to 1 if not specified).
    
    IMPORTANT: If an 'amenity_request' is identified, you MUST include the price of the amenity in your 'conci_response' and state that the cost will be added to their bill upon completion *ONLY IF THE GUEST IS CLEARLY REQUESTING THE AMENITY FOR DELIVERY*. If the guest is only asking about the price or availability, your 'conci_response' should provide the information without implying a delivery or adding to the bill.
    
    If the guest asks for information you cannot provide (like real-time weather, external locations, or current time) or if their request is unclear, state that you cannot fulfill that specific part of the request but offer to help with other hotel-related inquiries. Do not make up information.

    Your response should be a JSON object with the following structure:
    {{
        "intent": "request_type_string",
        "entities": {{
            "amenity_name": "string (if amenity_request)",
            "quantity": "integer (if amenity_request, default 1)",
            "query": "original_user_message_string"
            // other relevant entities as needed
        }},
        "conci_response": "Your natural language response to the guest."
    }}
    
    Ensure the "conci_response" is friendly and helpful.
    """
    
    chat_history.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "contents": chat_history,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "intent": {"type": "STRING"},
                    "entities": {
                        "type": "OBJECT",
                        "properties": {
                            "amenity_name": {"type": "STRING", "nullable": True},
                            "quantity": {"type": "INTEGER", "default": 1},
                            "query": {"type": "STRING"}
                        },
                    },
                    "conci_response": {"type": "STRING"}
                },
                "required": ["intent", "entities", "conci_response"]
            }
        },
        "system_instruction": {"parts": [{"text": system_instruction_text}]}
    }


    try:
        response = requests.post(
            GEMINI_API_URL,
            headers={'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY},
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            json_string = result['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(json_string)
            return parsed_json
        else:
            return {
                "intent": "general_inquiry",
                "entities": {"query": prompt},
                "conci_response": "I apologize, I could not process your request at this moment. Please try again or contact staff directly."
            }
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        # Print the response content for more details on 400 error
        if hasattr(e, 'response') and e.response is not None:
            print(f"Gemini API Error Response Content: {e.response.text}")
        return {
            "intent": "general_inquiry",
            "entities": {"query": prompt},
            "conci_response": "I'm having trouble connecting right now. Please try again in a moment."
        }
    except json.JSONDecodeError as e:
        print(f"Error decoding Gemini API response JSON: {e}")
        print("Raw Gemini response:", response.text if 'response' in locals() else "No response text")
        return {
            "intent": "general_inquiry",
            "entities": {"query": prompt},
            "conci_response": "I received an unexpected response. Could you please rephrase your request?"
        }
    except Exception as e:
        print(f"An unexpected error occurred in call_gemini_api: {e}")
        return {
            "intent": "general_inquiry",
            "entities": {"query": prompt},
            "conci_response": "An internal error occurred while processing your request. Please contact staff if the issue persists."
        }


# --- Guest Interface API Endpoints ---

@require_POST
async def process_guest_command(request):
    """
    API endpoint to process a guest's command (new message).
    This creates a new GuestRequest with 'pending' status if it's an actionable request,
    or just updates chat history if it's a casual chat.
    Matches URL: /api/process_command/
    Expects hotel_id and room_number in the JSON body.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message').strip()

        hotel_id = data.get('hotel_id')
        room_number = data.get('room_number')

        if not user_message or not hotel_id or not room_number:
            return JsonResponse({'success': False, 'error': 'Missing message, hotel_id, or room_number.'}, status=400)

        hotel = await sync_to_async(get_object_or_404)(Hotel, id=hotel_id)

        # Fetch available amenities with name and price
        available_amenities_data = await sync_to_async(list)(
            Amenity.objects.filter(is_available=True).values('name', 'price')
        )
        
        gemini_response = await call_gemini_api(user_message, available_amenities_data)
        
        request_type = gemini_response.get('intent', 'general_inquiry')
        conci_response = gemini_response.get('conci_response', "I apologize, I couldn't fully understand that. Can you please rephrase?")
        ai_entities = gemini_response.get('entities', {"query": user_message})

        amenity_obj = None
        amenity_qty = ai_entities.get('quantity', 1)

        is_actionable_amenity_request = False

        if request_type == 'amenity_request':
            amenity_name_from_ai = ai_entities.get('amenity_name')
            if amenity_name_from_ai:
                amenity_obj = await sync_to_async(Amenity.objects.filter(name__iexact=amenity_name_from_ai, is_available=True).first)()
                if not amenity_obj:
                    request_type = 'general_inquiry'
                    conci_response = f"I'm sorry, '{amenity_name_from_ai}' is not currently available or recognized as an amenity. Can I help with something else?"
                else:
                    # Check if the AI's response implies a delivery/action, not just info.
                    # This is a heuristic and might need fine-tuning based on AI's actual responses.
                    # Look for keywords that suggest confirmation of delivery or action.
                    conci_response_lower = conci_response.lower()
                    if "deliver" in conci_response_lower or \
                       "bring" in conci_response_lower or \
                       "send" in conci_response_lower or \
                       "on its way" in conci_response_lower or \
                       "will be added to your bill" in conci_response_lower:
                        is_actionable_amenity_request = True
            else:
                request_type = 'general_inquiry'
                conci_response = "I understand you're looking for an amenity, but I didn't catch which one. Could you please specify?"


        latest_request_for_chat = await sync_to_async(GuestRequest.objects.filter(
            hotel=hotel,
            room_number=room_number
        ).order_by('-timestamp').first)()

        current_chat_history = []
        if latest_request_for_chat and latest_request_for_chat.chat_history:
            try:
                current_chat_history = json.loads(latest_request_for_chat.chat_history)
            except json.JSONDecodeError:
                current_chat_history = []

        current_chat_history.append({"role": "user", "parts": [{"text": user_message}]})
        current_chat_history.append({"role": "model", "parts": [{"text": conci_response}]})

        request_obj_id = None

        # Only create a new pending request if it's truly actionable
        if request_type == 'casual_chat' or (request_type == 'amenity_request' and not is_actionable_amenity_request):
            # For casual chats or amenity inquiries that are not actionable requests,
            # update the chat_history of the LATEST request or create a new one with 'completed' status.
            if latest_request_for_chat:
                latest_request_for_chat.chat_history = json.dumps(current_chat_history)
                await sync_to_async(latest_request_for_chat.save)()
                request_obj_id = latest_request_for_chat.id
            else:
                dummy_request = await sync_to_async(GuestRequest.objects.create)(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=user_message,
                    conci_response_text=conci_response,
                    status='completed', # Mark as completed so it doesn't show in staff pending
                    request_type='casual_chat', # Set type
                    chat_history=json.dumps(current_chat_history)
                )
                request_obj_id = dummy_request.id

        else: # This is an actionable request (e.g., maintenance, housekeeping, or an actionable amenity_request)
            request_obj = await sync_to_async(GuestRequest.objects.create)(
                hotel=hotel,
                room_number=room_number,
                raw_text=user_message,
                ai_intent=request_type,
                ai_entities=json.dumps(ai_entities),
                conci_response_text=conci_response,
                status='pending', # New actionable requests start as 'pending'
                request_type=request_type,
                amenity_requested=amenity_obj,
                amenity_quantity=amenity_qty,
                bill_added=False,
                chat_history=json.dumps(current_chat_history)
            )
            request_obj_id = request_obj.id
        
        return JsonResponse({
            'success': True,
            'conci_response': conci_response,
            'request_id': request_obj_id,
            'chat_history': current_chat_history,
        })

    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON in request body.")
    except Exception as e:
        print(f"Error processing guest command: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# --- Consolidated Staff Dashboard View ---
@login_required
def staff_dashboard(request, main_tab='home', sub_tab=None):
    """
    Renders the staff dashboard, handling different tabs (home, requests, guest_management)
    and sub-tabs for requests (active, archive, all).
    """
    user_hotel = None
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        logout(request)
        return redirect('login')
    except AttributeError: # Catches if request.user has no profile
        logout(request)
        return redirect('login')

    if not user_hotel:
        # If user has a profile but no hotel assigned (null=True, blank=True on Hotel FK)
        logout(request)
        return redirect('login')

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

    # --- Handle POST requests first (form submissions) ---
    if request.method == 'POST':
        # --- Handle Guest Assignment Form Submission ---
        # Identify guest assignment form by a unique field, e.g., 'guest_names' or 'room_number_input'
        if 'guest_names' in request.POST and 'room_number_input' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            
            if assignment_id:
                # Editing existing assignment
                assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=user_hotel)
                form = GuestRoomAssignmentForm(request.POST, instance=assignment, hotel=user_hotel)
            else:
                # Creating new assignment
                form = GuestRoomAssignmentForm(request.POST, hotel=user_hotel) 

            if form.is_valid():
                try:
                    form.save()
                    return JsonResponse({'success': True, 'message': 'Guest assignment saved successfully.'})
                except Exception as e:
                    # Log the actual server-side error for debugging
                    print(f"Server error saving guest assignment: {e}")
                    return JsonResponse({'success': False, 'error': f'A server error occurred: {str(e)}'}, status=500)
            else:
                # Print form errors to console for debugging
                print("Guest assignment form errors:", form.errors)
                # Return JSON response with errors for frontend
                return JsonResponse({'success': False, 'error': 'Validation failed.', 'errors': form.errors.as_json()}, status=400)

        # --- Handle Amenity Form Submission (if you have one in the same view) ---
        elif 'amenity_name' in request.POST: # Example field to identify AmenityForm
            amenity_id = request.POST.get('amenity_id')
            if amenity_id:
                amenity = get_object_or_404(Amenity, id=amenity_id)
                form = AmenityForm(request.POST, instance=amenity)
            else:
                form = AmenityForm(request.POST)

            if form.is_valid():
                form.save()
                return JsonResponse({'success': True, 'message': 'Amenity saved successfully.'})
            else:
                print("Amenity form errors:", form.errors)
                return JsonResponse({'success': False, 'error': 'Validation failed.', 'errors': form.errors.as_json()}, status=400)
        
        # --- Handle other POST requests if any ---
        # ... (add more elif blocks for other forms if needed) ...

        # If it's a POST but doesn't match any known form, return an error
        return JsonResponse({'success': False, 'error': 'Unknown form submission or invalid request.'}, status=400)

    # --- Handle GET requests (displaying the dashboard) ---
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
                # Filter by update_at or status change time if available, or just creation for simplicity
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

        # Default to 'active' if no sub_tab is specified
        if sub_tab is None:
            sub_tab = 'active'
            context['current_sub_tab'] = 'active' # Ensure template reflects default

        if sub_tab == 'active':
            # Active requests are those with 'pending' or 'in_progress' status
            # AND NOT 'casual_chat' type
            requests_for_hotel = requests_for_hotel.filter(status__in=['pending', 'in_progress']).exclude(request_type='casual_chat')
        elif sub_tab == 'archive':
            # Archived requests are completed or cancelled
            requests_for_hotel = requests_for_hotel.filter(status__in=['completed', 'cancelled'])
        elif sub_tab == 'all':
            # For 'all' tab, include all types, including casual_chat
            pass # No additional filter for 'all' beyond hotel

        requests_for_hotel = requests_for_hotel.order_by('-timestamp')

        # Group requests by type for display
        grouped_requests = {}
        # Use the order defined in the model choices for consistent display
        # Only iterate through actual REQUEST_TYPE_CHOICES to ensure all categories are considered
        for choice_value, choice_label in GuestRequest.REQUEST_TYPE_CHOICES:
            grouped_requests[choice_value] = {
                'display_name': choice_label,
                'requests': []
            }
        
        # Populate the grouped_requests
        for req in requests_for_hotel:
            # Note: This `first()` might pick an arbitrary assignment if multiple exist for the room.
            # You might want to refine this to get the *active* assignment for the room,
            # or ensure a request is linked to a specific assignment if that's your model's intent.
            assignment = GuestRoomAssignment.objects.filter(hotel=user_hotel, room_number=req.room_number).first()
            
            # Ensure the request_type from the DB matches one of our defined choices
            # This handles cases where old data might have undefined types
            actual_request_type = req.request_type if req.request_type in [cv for cv, cl in GuestRequest.REQUEST_TYPE_CHOICES] else 'general_inquiry'

            # Only add to grouped_requests if it's not a casual_chat for 'active' tab
            if sub_tab == 'active' and actual_request_type == 'casual_chat':
                continue # Skip casual chat for active view
            
            grouped_requests[actual_request_type]['requests'].append({
                'request': req,
                'assignment': assignment,
            })

        # Convert to a list of (display_name, list_of_requests) for ordered iteration in template
        # Filter out empty groups if they are not needed, unless it's the 'all' tab and we want to show all categories
        ordered_grouped_requests = []
        has_any_requests = False
        for choice_value, choice_label in GuestRequest.REQUEST_TYPE_CHOICES:
            # Only include non-casual chat types in the active view, or all types in the 'all'/'archive' views
            if (sub_tab == 'active' and choice_value == 'casual_chat'):
                continue # Skip casual chat for active tab
            
            if grouped_requests[choice_value]['requests']:
                ordered_grouped_requests.append(grouped_requests[choice_value])
                has_any_requests = True

        context['grouped_requests'] = ordered_grouped_requests
        context['has_any_requests'] = has_any_requests

    elif main_tab == 'guest_management':
        context['page_title'] = 'Guest Management'
        
        # Initialize an empty form for GET requests or if POST fails validation
        # This 'form' variable will be used in the template for the Add/Edit modal.
        form = GuestRoomAssignmentForm(hotel=user_hotel) 

        # Start with all assignments for the user's hotel
        all_assignments = GuestRoomAssignment.objects.filter(hotel=user_hotel)

        # --- Apply Filters ---
        filter_params = {}

        room_number_filter_val = request.GET.get('room_number')
        if room_number_filter_val:
            # --- CRITICAL FIX: Filter directly on the CharField 'room_number' ---
            all_assignments = all_assignments.filter(room_number__icontains=room_number_filter_val)
            filter_params['room_number'] = room_number_filter_val

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
                from_date = timezone.datetime.strptime(check_in_date_from, '%Y-%m-%d').date()
                all_assignments = all_assignments.filter(check_in_time__date__gte=from_date)
                filter_params['check_in_date_from'] = check_in_date_from
            except ValueError:
                pass

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
            'form': form, # Pass the form for the add/edit modal (initialized for GET)
            'all_assignments': all_assignments, # Pass the filtered assignments
            'assignment_status_choices': GuestRoomAssignment.STATUS_CHOICES, # Pass choices for status filter
            'filter_params': filter_params, # Pass current filter values to re-populate form fields
        })
            
    return render(request, 'main/staff_dashboard.html', context)
# --- New Amenity Management View ---
@login_required
def amenity_management(request):
    user_hotel = None
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        logout(request)
        return redirect('login')
    except AttributeError:
        logout(request)
        return redirect('login')

    if not user_hotel:
        logout(request)
        return redirect('login')

    amenities = Amenity.objects.all().order_by('name') # Get all amenities

    if request.method == 'POST':
        amenity_id = request.POST.get('amenity_id')
        if amenity_id:
            # Editing an existing amenity
            amenity_instance = get_object_or_404(Amenity, id=amenity_id)
            form = AmenityForm(request.POST, instance=amenity_instance)
        else:
            # Adding a new amenity
            form = AmenityForm(request.POST)
        
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Amenity saved successfully.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
    
    else: # GET request
        form = AmenityForm() # Empty form for adding new amenity

    context = {
        'page_title': 'Amenity Management',
        'current_main_tab': 'amenities', # Set a new main tab for amenities
        'form': form,
        'amenities': amenities,
    }
    return render(request, 'main/amenity_management.html', context)


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
                request_type__in=['maintenance', 'repairs', 'housekeeping', 'room_service', 'concierge', 'general_inquiry', 'amenity_request'], # Include amenity requests
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
    if request.method == 'POST':
        try:
            # Ensure the user has a hotel profile and access to this request
            user_hotel = request.user.profile.hotel
            req = get_object_or_404(GuestRequest, id=request_id, hotel=user_hotel)
            new_status = request.POST.get('new_status')
            
            # Print for debugging: what status is being received?
            print(f"Attempting to update request {request_id} to status: {new_status}")

            if new_status in dict(req.STATUS_CHOICES):
                # Special handling for 'amenity_request' when status changes to 'completed'
                if req.request_type == 'amenity_request' and new_status == 'completed' and not req.bill_added:
                    # Find the guest's current assignment for this room
                    guest_assignment = GuestRoomAssignment.objects.filter(
                        hotel=req.hotel,
                        room_number=req.room_number,
                        check_in_time__lte=timezone.localtime(timezone.now()),
                        check_out_time__gte=timezone.localtime(timezone.now()),
                        status='checked_in' # Only add to bill if guest is checked in
                    ).first()

                    if guest_assignment:
                        if req.amenity_requested and req.amenity_quantity > 0:
                            amenity_cost = req.amenity_requested.price * req.amenity_quantity
                            guest_assignment.total_bill_amount += amenity_cost
                            guest_assignment.save()
                            req.bill_added = True # Mark as billed
                            print(f"Added ${amenity_cost:.2f} for {req.amenity_quantity}x {req.amenity_requested.name} to Room {req.room_number}'s bill. New total: ${guest_assignment.total_bill_amount:.2f}")
                        else:
                            print(f"Warning: Amenity request {req.id} completed but amenity_requested or quantity missing. Bill not updated.")
                    else:
                        print(f"Warning: Amenity request {req.id} completed but no active guest assignment found for Room {req.room_number}. Bill not updated.")

                req.status = new_status
                req.save()
                
                # *** CRITICAL CHANGE: Return JSON response instead of redirect ***
                return JsonResponse({'success': True, 'message': 'Status updated successfully!'})
            else:
                # Invalid status provided
                print(f"Error: Invalid status '{new_status}' provided for request {request_id}.")
                return JsonResponse({'success': False, 'error': 'Invalid status provided.'}, status=400)
        except GuestRequest.DoesNotExist:
            print(f"Error: Request with ID {request_id} not found or not accessible.")
            return JsonResponse({'success': False, 'error': 'Request not found or unauthorized.'}, status=404)
        except Exception as e:
            # Log the actual error on your server for debugging
            print(f"Error updating request status: {e}")
            return JsonResponse({'success': False, 'error': f'A server error occurred: {str(e)}'}, status=500)
    else:
        # Not a POST request
        return JsonResponse({'success': False, 'error': 'Invalid request method. Only POST is allowed.'}, status=405)

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
            'ai_intent': ai_entities_data.get('intent', 'N/A'), # Use 'intent' from entities if available
            'ai_entities': ai_entities_data,
            'conci_response_text': req.conci_response_text or 'No response yet.',
            'status': req.get_status_display(),
            'request_type': req.get_request_type_display(), # New: display request type
            'timestamp': req.timestamp.isoformat(),
            'staff_notes': req.staff_notes or 'No notes.',
            'chat_history': chat_history_data,
            'amenity_details': None # Initialize amenity details
        }

        if req.request_type == 'amenity_request' and req.amenity_requested:
            details['amenity_details'] = {
                'name': req.amenity_requested.name,
                'quantity': req.amenity_quantity,
                'price_per_unit': float(req.amenity_requested.price), # Convert Decimal to float for JSON
                'total_amenity_cost': float(req.amenity_requested.price * req.amenity_quantity),
                'bill_added': req.bill_added
            }

        return JsonResponse(details)
    except Exception as e:
        print(f"Error fetching request details: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def edit_guest_assignment(request, assignment_id):
    """
    API endpoint to handle editing of a guest assignment via AJAX.
    Handles GET to fetch data and POST to save.
    Matches URL: /api/assignments/<int:assignment_id>/edit/
    """
    try:
        user_profile = request.user.profile
        user_hotel = user_profile.hotel
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)
    except AttributeError:
        return JsonResponse({'success': False, 'error': 'User profile not linked.'}, status=403)

    assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=user_hotel)

    if request.method == 'GET':
        # Logic to fetch data for the form
        # --- CRITICAL FIX: room_number is now a CharField directly on GuestRoomAssignment ---
        # So, assignment.room_number is already the string.
        room_number_str = assignment.room_number if assignment.room_number else ''
        
        data = {
            'success': True,
            'assignment': {
                'id': assignment.id,
                # Now we only send the room_number string, no 'id' for room_number object
                'room_number': { 'room_number': room_number_str }, 
                'guest_names': assignment.guest_names,
                'check_in_time': assignment.check_in_time.isoformat() if assignment.check_in_time else None,
                'check_out_time': assignment.check_out_time.isoformat() if assignment.check_out_time else None,
                'status': assignment.status,
                'total_bill_amount': str(assignment.total_bill_amount),
                'amount_paid': str(assignment.amount_paid),
            }
        }
        return JsonResponse(data)

    elif request.method == 'POST':
        # Your existing logic to handle saving the updated assignment
        mutable_post = request.POST.copy()

        check_in_date = mutable_post.get('check_in_date')
        check_in_time_input = mutable_post.get('check_in_time_input')
        if check_in_date and check_in_time_input:
            mutable_post['check_in_time'] = f"{check_in_date} {check_in_time_input}"
        
        check_out_date = mutable_post.get('check_out_date')
        check_out_time_input = mutable_post.get('check_out_time_input')
        if check_out_date and check_out_time_input:
            mutable_post['check_out_time'] = f"{check_out_date} {check_out_time_input}"

        form = GuestRoomAssignmentForm(mutable_post, instance=assignment, hotel=user_hotel)
        
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({'success': True, 'message': 'Assignment updated successfully.'})
            except Exception as e:
                print(f"Server error saving guest assignment (edit): {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({'success': False, 'error': f'A server error occurred: {str(e)}'}, status=500)
        else:
            print("Guest assignment edit form errors:", form.errors)
            return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed.'}, status=405)


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

# Make guest_interface an async function
async def guest_interface(request, hotel_id, room_number):
    """
    Renders the guest-facing interface for a specific room in a hotel.
    Matches URL: /guest/<int:hotel_id>/<str:room_number>/
    """
    # Use sync_to_async for get_object_or_404
    hotel = await sync_to_async(get_object_or_404)(Hotel, id=hotel_id)
    
    # Use sync_to_async for ORM query
    current_assignment = await sync_to_async(GuestRoomAssignment.objects.filter(
        hotel=hotel,
        room_number=room_number,
        check_in_time__lte=timezone.localtime(timezone.now()),
        check_out_time__gte=timezone.localtime(timezone.now())
    ).first)()

    # Get the latest request (any status) for chat history display
    # Use sync_to_async for ORM query
    latest_request_for_chat = await sync_to_async(GuestRequest.objects.filter(
        hotel=hotel,
        room_number=room_number
    ).order_by('-timestamp').first)()

    chat_history = []
    if latest_request_for_chat and latest_request_for_chat.chat_history:
        try:
            chat_history = json.loads(latest_request_for_chat.chat_history)
        except json.JSONDecodeError:
            chat_history = []

    context = {
        'hotel': hotel,
        'room_number': room_number,
        'guest_names': current_assignment.guest_names if current_assignment else "Guest",
        'latest_request_id': latest_request_for_chat.id if latest_request_for_chat else None,
        'chat_history': json.dumps(chat_history),
    }
    # Render is a synchronous function, no need for sync_to_async here
    return render(request, 'main/guest_interface.html', context)


# --- Guest Interface API Endpoints ---



@require_GET
async def check_for_new_updates(request, hotel_id, room_number):
    """
    API endpoint for the guest interface to check for new responses from Conci.
    Matches URL: /api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/
    """
    last_request_id = request.GET.get('last_request_id')
    
    # Use sync_to_async for get_object_or_404
    hotel = await sync_to_async(get_object_or_404)(Hotel, id=hotel_id)
    
    # Get the latest request for this room, regardless of status
    # Use sync_to_async for ORM query
    latest_request = await sync_to_async(GuestRequest.objects.filter(
        hotel=hotel,
        room_number=room_number
    ).order_by('-timestamp').first)()

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

# --- API Endpoints for Amenity Management (remain the same) ---

@login_required
@require_POST
def delete_amenity(request, amenity_id):
    """
    API endpoint to delete an amenity.
    """
    try:
        amenity = get_object_or_404(Amenity, id=amenity_id)
        amenity.delete()
        return JsonResponse({'success': True, 'message': 'Amenity deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

