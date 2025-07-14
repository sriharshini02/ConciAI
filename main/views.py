from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import os
import requests
from django.utils import timezone
from django import forms
import datetime

from .models import GuestRequest, Hotel, HotelConfiguration, GuestRoomAssignment, UserProfile

# Get API Key from settings.py (loaded from .env)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Helper function for Google Gemini API ---

def call_gemini_api(prompt_text, room_number, chat_history=[]):
    """
    Calls the Gemini API (gemini-2.0-flash) for text generation.
    Instructs Gemini to return a structured text output for easier parsing of intent/entities.
    """
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not set for Gemini API.")
        return {"success": False, "error": "API key not configured for Gemini."}

    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    
    # Define Conci's persona and provide room number context
    initial_persona_prompt = (
        f"You are Conci, a helpful and polite AI hotel assistant for Room {room_number}. "
        "Your goal is to assist guests with their requests and provide information about the hotel. "
        "Keep your responses concise, friendly, and directly address the guest's needs. "
        "Based on the conversation history and the current guest message, "
        "determine the primary intent and any relevant entities. "
        "If it's a request for an amenity, identify the 'item' (e.g., 'towel', 'water') and 'quantity' (default to 1 if not specified). "
        "If it's a request for information, identify the 'info_type' (e.g., 'wifi_password', 'checkout_time', 'bill_details', 'guest_names'). "
        "If the guest asks for a menu (e.g., 'send menu', 'food menu', 'restaurant menu'), "
        "the intent should be 'request_menu'. Do NOT mention a 'room service tablet' or 'sending menu electronically'. "
        "Instead, for menu requests, respond that staff will bring a physical copy shortly. "
        "If the guest's message is purely a clarification or part of an ongoing request for an *already identified* primary actionable item (like confirming quantity of an amenity), "
        "then re-affirm the *same* primary intent and update the entities as needed. "
        "If it's a general greeting, farewell, or casual chat, use 'general_chat'. "
        "If you cannot determine a clear intent, use 'unknown_query'.\n\n"
        "Format your response like this:\n"
        "RESPONSE: [Conci's conversational response]\n"
        "INTENT: [ai_intent]\n"
        "ENTITIES: [JSON string of entities, e.g., {'item': 'towel', 'quantity': 1} or {}]"
    )

    # Construct the full conversation payload for Gemini
    contents = []
    contents.append({"role": "user", "parts": [{"text": initial_persona_prompt}]})
    contents.append({"role": "model", "parts": [{"text": "Hello! How may I assist you today?"}]})

    for turn in chat_history:
        contents.append(turn)

    contents.append({"role": "user", "parts": [{"text": prompt_text}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "topK": 40,
            "maxOutputTokens": 200,
        }
    }

    try:
        response = requests.post(apiUrl, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        conci_response_text = "I'm sorry, I couldn't process your request at the moment. Please try again."
        ai_intent = "unknown_query"
        ai_entities = {}

        if result.get("candidates") and len(result["candidates"]) > 0 and result["candidates"][0]["content"]["parts"]:
            gemini_raw_response_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Parse the structured text output
            lines = gemini_raw_response_text.split('\n')
            
            for line in lines:
                if line.startswith("RESPONSE:"):
                    conci_response_text = line.replace("RESPONSE:", "").strip()
                elif line.startswith("INTENT:"):
                    ai_intent = line.replace("INTENT:", "").strip()
                elif line.startswith("ENTITIES:"):
                    entities_str = line.replace("ENTITIES:", "").strip()
                    try:
                        ai_entities = json.loads(entities_str)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse entities JSON: {entities_str}")
                        ai_entities = {}
            
            if not conci_response_text or not any(line.startswith("RESPONSE:") for line in lines):
                 conci_response_text = gemini_raw_response_text.split('\n')[0].strip()


            return {
                "success": True,
                "ai_intent": ai_intent,
                "ai_entities": ai_entities,
                "conci_response_text": conci_response_text
            }
        else:
            print(f"Gemini API response did not contain valid candidates or content: {result}")
            return {"success": False, "error": "AI could not generate a valid response."}

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return {"success": False, "error": f"Failed to connect to Gemini AI: {e}"}
    except Exception as e:
        print(f"Unexpected error in Gemini API call: {e}")
        return {"success": False, "error": f"An unexpected error occurred with Gemini: {e}"}


@login_required
def staff_dashboard(request, status_filter=None):
    """
    Renders the hotel staff dashboard.
    Displays guest requests based on status_filter, ordered by most recent,
    and includes associated guest room assignment details, filtered by the logged-in user's hotel.
    Also calculates and displays room analytics.
    """
    try:
        user_profile = request.user.profile
        staff_hotel = user_profile.hotel
        if not staff_hotel:
            return render(request, 'main/error_page.html', {'message': 'Your account is not assigned to a hotel. Please contact an administrator.'})
    except UserProfile.DoesNotExist:
        return render(request, 'main/error_page.html', {'message': 'User profile not found. Please contact an administrator.'})

    if status_filter is None:
        status_filter = ['pending', 'in_progress']
    
    requests_queryset = GuestRequest.objects.filter(hotel=staff_hotel, status__in=status_filter)
    
    requests = requests_queryset.order_by('-timestamp')
    
    requests_with_details = []
    now = timezone.now()

    active_assignments = {}
    current_assignments_queryset = GuestRoomAssignment.objects.filter(
        hotel=staff_hotel,
        check_in_time__lte=now,
        check_out_time__gte=now
    ).order_by('-check_in_time') 

    for assignment in current_assignments_queryset:
        if assignment.room_number not in active_assignments:
            active_assignments[assignment.room_number] = assignment

    for req in requests:
        assignment_info = active_assignments.get(req.room_number)
        
        requests_with_details.append({
            'request': req,
            'assignment': assignment_info
        })

    total_rooms = staff_hotel.total_rooms
    
    currently_occupied_rooms = GuestRoomAssignment.objects.filter(
        hotel=staff_hotel,
        check_in_time__lte=now,
        check_out_time__gte=now
    ).values_list('room_number', flat=True).distinct()
    
    filled_rooms = currently_occupied_rooms.count()
    available_rooms = total_rooms - filled_rooms

    context = {
        'requests_with_details': requests_with_details,
        'page_title': 'Conci Staff Dashboard',
        'current_tab_status': status_filter,
        'total_rooms': total_rooms,
        'filled_rooms': filled_rooms,
        'available_rooms': available_rooms,
        'staff_hotel_name': staff_hotel.name,
    }
    return render(request, 'main/staff_dashboard.html', context)


@require_POST
@login_required
def update_request_status(request, request_id):
    """
    Handles updating the status of a guest request via POST request.
    Expected to be called via AJAX from the staff dashboard.
    """
    try:
        user_profile = request.user.profile
        staff_hotel = user_profile.hotel
        if not staff_hotel:
            return JsonResponse({'success': False, 'error': 'Your account is not assigned to a hotel.'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)

    guest_request = get_object_or_404(GuestRequest, id=request_id, hotel=staff_hotel)
    new_status = request.POST.get('new_status')
    valid_statuses = [choice[0] for choice in guest_request.STATUS_CHOICES]
    if new_status and new_status in valid_statuses:
        guest_request.status = new_status
        guest_request.save()
        return JsonResponse({'success': True, 'message': f"Status for Room {guest_request.room_number} updated to {guest_request.get_status_display()}."}) # type: ignore
    else:
        return JsonResponse({'success': False, 'error': "Invalid status provided."}, status=400)


def guest_interface(request, hotel_id, room_number):
    """
    Renders the simulated Conci device interface for a specific room within a specific hotel.
    """
    hotel = get_object_or_404(Hotel, id=hotel_id)

    context = {
        'hotel_name': hotel.name,
        'room_number': room_number,
        'page_title': f'Conci Device - Room {room_number}',
        'current_status': 'idle',
        'hotel_id': hotel.id, # type: ignore
        'room_number_str': room_number,
    }
    return render(request, 'main/guest_interface.html', context)


@csrf_exempt
@require_POST
def process_guest_command(request):
    """
    Receives guest commands from the simulated device, processes with AI.
    It DOES NOT save to DB directly for actionable intents.
    Instead, it returns AI analysis for frontend to manage draft requests.
    """
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            room_number = data.get('room_number')
            raw_text = data.get('command')
            hotel_id = data.get('hotel_id')
            chat_history = data.get('history', [])
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON format.'}, status=400)
    else:
        room_number = request.POST.get('room_number')
        raw_text = request.POST.get('command')
        hotel_id = request.POST.get('hotel_id')
        chat_history = json.loads(request.POST.get('history', '[]'))

    if not all([room_number, raw_text, hotel_id]):
        return JsonResponse({'success': False, 'error': 'Missing data: room_number, command, or hotel_id.'}, status=400)

    try:
        hotel = get_object_or_404(Hotel, id=hotel_id)

        # --- Check for specific hotel information requests before calling Gemini ---
        raw_text_lower = raw_text.lower()
        
        now = timezone.now()
        current_assignment = GuestRoomAssignment.objects.filter(
            hotel=hotel,
            room_number=room_number,
            check_in_time__lte=now,
            check_out_time__gte=now
        ).order_by('-check_in_time').first()

        # --- Direct Lookups for Guest Assignment Info (Still save directly as they are immediate info) ---
        if "checkout" in raw_text_lower or "check out" in raw_text_lower or \
           "checkin" in raw_text_lower or "check in" in raw_text_lower or \
           "bill" in raw_text_lower or "amount" in raw_text_lower or "paid" in raw_text_lower or \
           "guest name" in raw_text_lower or "names" in raw_text_lower or "who is staying" in raw_text_lower:
            
            conci_response_text = ""
            ai_entities = {}
            ai_intent = "get_info" # Default for these direct info requests

            if current_assignment:
                if "checkout" in raw_text_lower or "check out" in raw_text_lower:
                    conci_response_text = (
                        f"Your scheduled checkout time is "
                        f"{current_assignment.check_out_time.strftime('%B %d, %I:%M %p')}. "
                        f"Is there anything else I can assist you with?"
                    )
                    ai_entities = {'info_type': 'checkout_time'}
                elif "checkin" in raw_text_lower or "check in" in raw_text_lower:
                     conci_response_text = (
                        f"Your scheduled check-in time was "
                        f"{current_assignment.check_in_time.strftime('%B %d, %I:%M %p')}. "
                        f"Is there anything you need help with regarding your check-in?"
                    )
                     ai_entities = {'info_type': 'checkin_time'}
                elif "bill" in raw_text_lower or "amount" in raw_text_lower or "paid" in raw_text_lower:
                    balance_due = current_assignment.bill_amount - current_assignment.amount_paid
                    conci_response_text = (
                        f"Your total bill amount is ${current_assignment.bill_amount:.2f}, "
                        f"and you have paid ${current_assignment.amount_paid:.2f} so far. "
                        f"Your current balance due is ${balance_due:.2f}. "
                        f"Would you like more details or assistance with payment?"
                    )
                    ai_entities = {'info_type': 'bill_details', 'bill_amount': float(current_assignment.bill_amount), 'amount_paid': float(current_assignment.amount_paid)}
                elif "guest name" in raw_text_lower or "names" in raw_text_lower or "who is staying" in raw_text_lower:
                    guest_names_display = current_assignment.guest_names if current_assignment.guest_names else "not specified for this assignment"
                    conci_response_text = (
                        f"The guest(s) associated with this room assignment are: {guest_names_display}. "
                        f"How else may I help you today?"
                    )
                    ai_entities = {'info_type': 'guest_names', 'names': guest_names_display}
                else:
                    conci_response_text = "I found your reservation details. What specific information are you looking for?"
                    ai_entities = {'info_type': 'reservation_details'}
                
                # These info requests are still directly saved as 'completed'
                GuestRequest.objects.create(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=raw_text,
                    ai_intent=ai_intent,
                    ai_entities=ai_entities,
                    conci_response_text=conci_response_text,
                    status='completed',
                    timestamp=timezone.now()
                )
                print(f"Saved GuestRequest for Room {room_number} with intent: {ai_intent} (from GuestRoomAssignment lookup)")
                
                return JsonResponse({
                    'success': True,
                    'response_text': conci_response_text,
                    'ai_intent': ai_intent, # Return intent/entities for frontend to know it's handled
                    'ai_entities': ai_entities
                })
            else:
                # Fallback if no current assignment found for detailed queries
                if "checkout" in raw_text_lower or "check out" in raw_text_lower:
                    checkout_config = HotelConfiguration.objects.filter(
                        hotel=hotel, key='checkout_time'
                    ).first()
                    if checkout_config:
                        conci_response_text = f"The standard checkout time for {hotel.name} is {checkout_config.value}. For specific reservation details, please contact the front desk."
                        ai_entities = {'info_type': 'standard_checkout_time'}
                    else:
                        conci_response_text = "I apologize, I can't find the standard checkout time. Please contact the front desk."
                elif "bill" in raw_text_lower or "amount" in raw_text_lower or "paid" in raw_text_lower or \
                     "guest name" in raw_text_lower or "names" in raw_text_lower or "who is staying" in raw_text_lower:
                    conci_response_text = "I apologize, I can't find specific reservation details for this room at the moment. Please contact the front desk for assistance."
                    ai_entities = {'info_type': 'reservation_details_not_found'}
                else:
                    conci_response_text = "I couldn't find specific reservation details. Is there something else I can help with?"
                    ai_entities = {'info_type': 'unknown_reservation_query'}

                GuestRequest.objects.create(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=raw_text,
                    ai_intent=ai_intent,
                    ai_entities=ai_entities,
                    conci_response_text=conci_response_text,
                    status='completed',
                    timestamp=timezone.now()
                )
                print(f"Saved GuestRequest for Room {room_number} with intent: {ai_intent} (no assignment found / general lookup)")
                return JsonResponse({
                    'success': True,
                    'response_text': conci_response_text,
                    'ai_intent': ai_intent,
                    'ai_entities': ai_entities
                })

        # --- Original Wi-Fi Lookup (Still save directly as it's immediate info) ---
        elif "wifi" in raw_text_lower or "internet" in raw_text_lower:
            wifi_config = HotelConfiguration.objects.filter(
                hotel=hotel, key='wifi_password'
            ).first()
            conci_response_text = ""
            ai_intent = "get_info"
            ai_entities = {'info_type': 'wifi_password'}
            if wifi_config:
                conci_response_text = f"The Wi-Fi password for {hotel.name} is {wifi_config.value}. You can connect to the '{wifi_config.value}' network. Please let me know if you need further assistance."
            else:
                conci_response_text = "I'm sorry, I don't have the Wi-Fi password readily available. Please contact the front desk."
            
            GuestRequest.objects.create(
                hotel=hotel,
                room_number=room_number,
                raw_text=raw_text,
                ai_intent=ai_intent,
                ai_entities=ai_entities,
                conci_response_text=conci_response_text,
                status='completed',
                timestamp=timezone.now()
            )
            print(f"Saved GuestRequest for Room {room_number} with intent: {ai_intent} (from direct lookup)")
            return JsonResponse({
                'success': True,
                'response_text': conci_response_text,
                'ai_intent': ai_intent,
                'ai_entities': ai_entities
            })
        # --- END OF DIRECT HOTEL INFO LOOKUP ---

        # If not handled by direct lookup, proceed with AI processing
        gemini_response_data = call_gemini_api(raw_text, room_number=room_number, chat_history=chat_history)
        if not gemini_response_data.get("success"):
            print(f"Gemini API call failed: {gemini_response_data.get('error')}")
            return JsonResponse({'success': False, 'error': gemini_response_data.get("error", "Gemini AI processing failed.")}, status=500)
        
        ai_intent = gemini_response_data['ai_intent']
        ai_entities = gemini_response_data['ai_entities']
        conci_response_text = gemini_response_data['conci_response_text']

        # --- IMPORTANT CHANGE: DO NOT SAVE ACTIONABLE REQUESTS HERE.
        #     Return AI analysis for frontend to manage as draft. ---
        
        print(f"AI processed command for Room {room_number}. Intent: {ai_intent}. Returning to frontend for draft management.")

        return JsonResponse({
            'success': True,
            'response_text': conci_response_text,
            'ai_intent': ai_intent, # Return AI intent
            'ai_entities': ai_entities # Return AI entities
        })

    except Hotel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Hotel not found.'}, status=404)
    except Exception as e:
        print(f"Unhandled error in process_guest_command: {e}")
        return JsonResponse({'success': False, 'error': f"An unhandled server error occurred: {str(e)}"}, status=500)


class GuestRoomAssignmentForm(forms.ModelForm):
    # Separate date and time fields for better UX (these are NOT directly model fields)
    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    check_in_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    check_out_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    check_out_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    # Explicitly define the DateTimeFields from the model and set them as NOT required
    # Their values will be set by the clean method. Use HiddenInput for their widget.
    check_in_time = forms.DateTimeField(required=False, widget=forms.HiddenInput())
    check_out_time = forms.DateTimeField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = GuestRoomAssignment
        fields = [
            'hotel', 'room_number', 'guest_names',
            'check_in_time',
            'check_out_time',
            'bill_amount', 'amount_paid'
        ]
        # Removed widgets from here as they are defined for custom fields above

    # Override __init__ to handle initial data for date/time fields when editing
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk: # If an existing instance is being edited
            # Populate the separate date/time fields from the instance's DateTimeFields
            if self.instance.check_in_time:
                self.initial['check_in_date'] = self.instance.check_in_time.date()
                self.initial['check_in_time_input'] = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.initial['check_out_date'] = self.instance.check_out_time.date()
                self.initial['check_out_time_input'] = self.instance.check_out_time.time()


    def clean(self):
        cleaned_data = super().clean()
        
        # Retrieve values for the custom form fields
        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_val = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_val = cleaned_data.get('check_out_time_input')

        # Process check-in time
        if check_in_date and check_in_time_val:
            try:
                combined_check_in = datetime.datetime.combine(check_in_date, check_in_time_val)
                cleaned_data['check_in_time'] = timezone.make_aware(combined_check_in)
            except TypeError as e:
                self.add_error('check_in_date', "Invalid check-in date or time format. Ensure both are correctly entered.")
                self.add_error('check_in_time_input', "Invalid check-in date or time format. Ensure both are correctly entered.")
                if 'check_in_time' in cleaned_data:
                    del cleaned_data['check_in_time']
        else:
            if check_in_date is None:
                self.add_error('check_in_date', "Check-in date is required.")
            if check_in_time_val is None:
                self.add_error('check_in_time_input', "Check-in time is required.")
            if 'check_in_time' in cleaned_data:
                del cleaned_data['check_in_time']

        # Process check-out time
        if check_out_date and check_out_time_val:
            try:
                combined_check_out = datetime.datetime.combine(check_out_date, check_out_time_val)
                cleaned_data['check_out_time'] = timezone.make_aware(combined_check_out)
            except TypeError as e:
                self.add_error('check_out_date', "Invalid check-out date or time format. Ensure both are correctly entered.")
                self.add_error('check_out_time_input', "Invalid check-out date or time format. Ensure both are correctly entered.")
                if 'check_out_time' in cleaned_data:
                    del cleaned_data['check_out_time']
        else:
            if check_out_date is None:
                self.add_error('check_out_date', "Check-out date is required.")
            if check_out_time_val is None:
                self.add_error('check_out_time_input', "Check-out time is required.")
            if 'check_out_time' in cleaned_data:
                del cleaned_data['check_out_time']

        # Basic validation: ensure check-out is strictly after check-in
        if 'check_in_time' in cleaned_data and 'check_out_time' in cleaned_data:
            if cleaned_data['check_out_time'] <= cleaned_data['check_in_time']:
                self.add_error(None, "Check-out time must be strictly after check-in time.")
        
        # Validation for bill_amount vs amount_paid
        bill_amount = cleaned_data.get('bill_amount')
        amount_paid = cleaned_data.get('amount_paid')

        if bill_amount is not None and amount_paid is not None:
            if amount_paid > bill_amount:
                self.add_error('amount_paid', "Amount paid cannot be greater than the total bill amount.")

        # NEW VALIDATION: Check for overlapping room assignments
        hotel = cleaned_data.get('hotel')
        room_number = cleaned_data.get('room_number')
        new_check_in_time = cleaned_data.get('check_in_time')
        new_check_out_time = cleaned_data.get('check_out_time')

        if hotel and room_number and new_check_in_time and new_check_out_time:
            overlapping_assignments = GuestRoomAssignment.objects.filter(
                hotel=hotel,
                room_number=room_number,
                check_in_time__lt=new_check_out_time,
                check_out_time__gt=new_check_in_time
            )

            if self.instance and self.instance.pk:
                overlapping_assignments = overlapping_assignments.exclude(pk=self.instance.pk)

            if overlapping_assignments.exists():
                self.add_error(None, "This room is already booked for the specified period.")
        
        return cleaned_data


@login_required
def guest_management_view(request):
    """
    Handles the display and submission of GuestRoomAssignment forms.
    Allows staff to add new guest assignments, filtered by their hotel.
    Displays all assignments for the hotel.
    """
    try:
        user_profile = request.user.profile
        staff_hotel = user_profile.hotel
        if not staff_hotel:
            return render(request, 'main/error_page.html', {'message': 'Your account is not assigned to a hotel. Please contact an administrator.'})
    except UserProfile.DoesNotExist:
        return render(request, 'main/error_page.html', {'message': 'User profile not found. Please contact an administrator.'})

    if request.method == 'POST':
        # This branch handles ADDING new assignments
        # Create a mutable copy of request.POST
        post_data = request.POST.copy()
        # Explicitly set the hotel to the staff's hotel before passing to the form
        post_data['hotel'] = staff_hotel.id # Use the ID of the staff's hotel

        form = GuestRoomAssignmentForm(post_data) # Pass the modified POST data
        if form.is_valid():
            # The form.cleaned_data['hotel'] will now correctly contain staff_hotel
            # No need for the extra check: if form.cleaned_data['hotel'] != staff_hotel:
            form.save()
            print("Form saved successfully!")
            return JsonResponse({'success': True, 'message': 'Guest assignment added successfully!'})
        else:
            print("Form errors (from POST):", form.errors) 
            return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
    else:
        # This branch handles rendering the page with the empty form and list of assignments
        form = GuestRoomAssignmentForm(initial={'hotel': staff_hotel})
        form.fields['hotel'].queryset = Hotel.objects.filter(pk=staff_hotel.pk) # type: ignore
        form.fields['hotel'].empty_label = None # type: ignore
        form.fields['hotel'].widget.attrs['disabled'] = 'disabled'

    # Fetch all assignments for the staff's hotel, ordered by check-in time
    all_assignments = GuestRoomAssignment.objects.filter(
        hotel=staff_hotel
    ).order_by('-check_in_time') # Order by most recent check-in first

    context = {
        'page_title': 'Conci Guest Management',
        'form': form,
        'all_assignments': all_assignments, # Pass all assignments to the template
        'staff_hotel_name': staff_hotel.name,
    }
    return render(request, 'main/guest_management.html', context)


@login_required
@require_POST
def edit_guest_assignment(request, assignment_id):
    """
    Handles editing an existing GuestRoomAssignment.
    Expected to be called via AJAX POST request.
    """
    try:
        user_profile = request.user.profile
        staff_hotel = user_profile.hotel
        if not staff_hotel:
            return JsonResponse({'success': False, 'error': 'Your account is not assigned to a hotel.'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)

    assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=staff_hotel) # Ensure staff can only edit their hotel's assignments

    # Create a mutable copy of request.POST
    post_data = request.POST.copy()
    # Explicitly set the hotel to the staff's hotel before passing to the form
    post_data['hotel'] = staff_hotel.id # Use the ID of the staff's hotel

    form = GuestRoomAssignmentForm(post_data, instance=assignment) # Pass the modified POST data
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Guest assignment updated successfully!'})
    else:
        print("Edit Form errors:", form.errors)
        return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)


@login_required
@require_POST
def delete_guest_assignment(request, assignment_id):
    """
    Handles deleting a GuestRoomAssignment.
    Expected to be called via AJAX POST request.
    """
    try:
        user_profile = request.user.profile
        staff_hotel = user_profile.hotel
        if not staff_hotel:
            return JsonResponse({'success': False, 'error': 'Your account is not assigned to a hotel.'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)

    assignment = get_object_or_404(GuestRoomAssignment, id=assignment_id, hotel=staff_hotel) # Ensure staff can only delete their hotel's assignments
    
    try:
        assignment.delete()
        return JsonResponse({'success': True, 'message': 'Guest assignment deleted successfully!'})
    except Exception as e:
        print(f"Error deleting assignment: {e}")
        return JsonResponse({'success': False, 'error': f'Failed to delete assignment: {str(e)}'}, status=500)



@csrf_exempt # IMPORTANT: This is for development convenience only. Remove in production!
@require_POST
def submit_draft_requests(request):
    """
    Receives a batch of draft requests from the frontend and saves them to the database.
    """
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            hotel_id = data.get('hotel_id')
            requests_to_save = data.get('requests', [])
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON format.'}, status=400)
    else:
        return JsonResponse({'success': False, 'error': 'Only JSON content type is supported for this endpoint.'}, status=400)

    if not hotel_id or not isinstance(requests_to_save, list):
        return JsonResponse({'success': False, 'error': 'Missing hotel_id or requests list.'}, status=400)

    try:
        hotel = get_object_or_404(Hotel, id=hotel_id)
        
        saved_count = 0
        for req_data in requests_to_save:
            # Validate and save each request from the batch
            room_number = req_data.get('room_number')
            raw_text = req_data.get('raw_text')
            ai_intent = req_data.get('ai_intent')
            ai_entities = req_data.get('ai_entities', {})
            conci_response_text = req_data.get('conci_response_text')
            status = req_data.get('status', 'pending') # Default to pending if not specified by frontend
            timestamp_str = req_data.get('timestamp')

            if not all([room_number, raw_text, ai_intent, conci_response_text, timestamp_str]):
                print(f"Skipping malformed request in batch: {req_data}")
                continue # Skip this request if essential data is missing

            # Convert ISO string timestamp back to datetime object
            try:
                # Python 3.11+ can parse ISO directly, but older versions might need a format string
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                timestamp = timezone.make_aware(timestamp) # Ensure it's timezone-aware
            except ValueError:
                print(f"Invalid timestamp format for request: {timestamp_str}. Using current time.")
                timestamp = timezone.now()

            # Create the GuestRequest object
            GuestRequest.objects.create(
                hotel=hotel,
                room_number=room_number,
                raw_text=raw_text,
                ai_intent=ai_intent,
                ai_entities=ai_entities,
                conci_response_text=conci_response_text,
                status=status,
                timestamp=timestamp # Use the timestamp from the frontend
            )
            saved_count += 1
        
        return JsonResponse({'success': True, 'message': f'Successfully saved {saved_count} request(s).'})

    except Hotel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Hotel not found.'}, status=404)
    except Exception as e:
        print(f"Unhandled error in submit_draft_requests: {e}")
        return JsonResponse({'success': False, 'error': f"An unhandled server error occurred: {str(e)}"}, status=500)
