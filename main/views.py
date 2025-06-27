from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import (
    csrf_exempt,
)  # IMPORTANT: Temporarily for API endpoint. Remove in production!
import json
import os  # To access environment variables
import requests  # For making HTTP calls to APIs
from django.utils import timezone

from .models import GuestRequest, Hotel, HotelConfiguration

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

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    # Define Conci's persona and provide room number context
    initial_persona_prompt = (
        f"You are Conci, a helpful and polite AI hotel assistant for Room {room_number}. "
        "Your goal is to assist guests with their requests and provide information about the hotel. "
        "Keep your responses concise, friendly, and directly address the guest's needs. "
        "Based on the conversation history and the current guest message, "
        "determine the primary intent and any relevant entities. "
        "If it's a request for an amenity, identify the 'item' (e.g., 'towel') and 'quantity' (default to 1 if not specified). "
        "If it's a request for information, identify the 'info_type' (e.g., 'wifi_password', 'checkout_time'). "
        "If the guest asks for a menu (e.g., 'send menu', 'food menu', 'restaurant menu'), "
        "the intent should be 'request_menu'. Do NOT mention a 'room service tablet' or 'sending menu electronically'. "
        "Instead, for menu requests, respond that staff will bring a physical copy shortly. "
        "If the guest's message is purely a clarification or part of an ongoing request, and does not represent a *new* distinct request, "
        "you should re-affirm the *previous* primary intent or state 'general_chat' if it's just a simple acknowledgement. "
        "If after clarifications, an actionable request is confirmed, then use the appropriate intent like 'request_amenity' or 'request_menu'. "  # More explicit guidance
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
    contents.append(
        {"role": "model", "parts": [{"text": "Hello! How may I assist you today?"}]}
    )

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
        },
    }

    try:
        response = requests.post(
            api_url, headers={"Content-Type": "application/json"}, json=payload
        )
        response.raise_for_status()

        result = response.json()

        conci_response_text = "I'm sorry, I couldn't process your request at the moment. Please try again."
        ai_intent = "unknown_query"
        ai_entities = {}

        if (
            result.get("candidates")
            and len(result["candidates"]) > 0
            and result["candidates"][0]["content"]["parts"]
        ):
            gemini_raw_response_text = result["candidates"][0]["content"]["parts"][0][
                "text"
            ].strip()

            # Parse the structured text output
            lines = gemini_raw_response_text.split("\n")

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

            if not conci_response_text or not any(
                line.startswith("RESPONSE:") for line in lines
            ):
                conci_response_text = gemini_raw_response_text.split("\n")[0].strip()

            return {
                "success": True,
                "ai_intent": ai_intent,
                "ai_entities": ai_entities,
                "conci_response_text": conci_response_text,
            }
        else:
            print(
                f"Gemini API response did not contain valid candidates or content: {result}"
            )
            return {
                "success": False,
                "error": "AI could not generate a valid response.",
            }

    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return {"success": False, "error": f"Failed to connect to Gemini AI: {e}"}
    except Exception as e:
        print(f"Unexpected error in Gemini API call: {e}")
        return {
            "success": False,
            "error": f"An unexpected error occurred with Gemini: {e}",
        }


# Staff Dashboard View (existing code, no changes needed)
def staff_dashboard(request):
    """
    Renders the hotel staff dashboard.
    Displays all guest requests, ordered by most recent.
    """
    requests = GuestRequest.objects.all().order_by("-timestamp")
    context = {
        "requests": requests,
        "page_title": "Conci Staff Dashboard",
    }
    return render(request, "main/staff_dashboard.html", context)


@require_POST
def update_request_status(request, request_id):
    """
    Handles updating the status of a guest request via POST request.
    Expected to be called via AJAX from the staff dashboard.
    """
    guest_request = get_object_or_404(GuestRequest, id=request_id)
    new_status = request.POST.get("new_status")
    valid_statuses = [choice[0] for choice in guest_request.STATUS_CHOICES]
    if new_status and new_status in valid_statuses:
        guest_request.status = new_status
        guest_request.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"Status for Room {guest_request.room_number} updated to {guest_request.get_status_display()}.",  # type: ignore
            }
        )
    else:
        return JsonResponse(
            {"success": False, "error": "Invalid status provided."}, status=400
        )


# Guest Interface View (existing code, no changes needed)
def guest_interface(request, room_number):
    """
    Renders the simulated Conci device interface for a specific room.
    """
    hotel = Hotel.objects.first()

    if not hotel:
        return render(
            request,
            "main/error_page.html",
            {"message": "No hotel configured. Please add a hotel via Django Admin."},
        )

    context = {
        "hotel_name": hotel.name,
        "room_number": room_number,
        "page_title": f"Conci Device - Room {room_number}",
        "current_status": "idle",
        "hotel_id": hotel.id,  # type: ignore
        "room_number_str": room_number,
    }
    return render(request, "main/guest_interface.html", context)


@csrf_exempt  # IMPORTANT: This is for development convenience only. Remove in production!
@require_POST
def process_guest_command(request):
    """
    Receives guest commands from the simulated device, processes with AI,
    saves to DB conditionally based on intent, and returns AI response text.
    Handles updating existing requests for ongoing conversations.
    """
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
            room_number = data.get("room_number")
            raw_text = data.get("command")
            hotel_id = data.get("hotel_id")
            chat_history = data.get("history", [])
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON format."}, status=400
            )
    else:
        room_number = request.POST.get("room_number")
        raw_text = request.POST.get("command")
        hotel_id = request.POST.get("hotel_id")
        chat_history = json.loads(request.POST.get("history", "[]"))

    if not all([room_number, raw_text, hotel_id]):
        return JsonResponse(
            {
                "success": False,
                "error": "Missing data: room_number, command, or hotel_id.",
            },
            status=400,
        )

    try:
        hotel = get_object_or_404(Hotel, id=hotel_id)

        # --- Check for specific hotel information requests before calling Gemini ---
        raw_text_lower = raw_text.lower()
        if "checkout" in raw_text_lower or "check out" in raw_text_lower:
            checkout_config = HotelConfiguration.objects.filter(
                hotel=hotel, key="checkout_time"
            ).first()
            if checkout_config:
                conci_response_text = f"The standard checkout time for {hotel.name} is {checkout_config.value}. Your specific checkout time might vary based on your booking. Would you like me to confirm it with the front desk?"
                ai_intent = "get_info"
                ai_entities = {"info_type": "checkout_time"}
                GuestRequest.objects.create(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=raw_text,
                    ai_intent=ai_intent,
                    ai_entities=ai_entities,
                    conci_response_text=conci_response_text,
                    status="completed",
                    timestamp=timezone.now(),
                )
                print(
                    f"Saved GuestRequest for Room {room_number} with intent: {ai_intent} (from direct lookup)"
                )
                return JsonResponse(
                    {
                        "success": True,
                        "response_text": conci_response_text,
                    }
                )
        elif "wifi" in raw_text_lower or "internet" in raw_text_lower:
            wifi_config = HotelConfiguration.objects.filter(
                hotel=hotel, key="wifi_password"
            ).first()
            if wifi_config:
                conci_response_text = f"The Wi-Fi password for {hotel.name} is {wifi_config.value}. You can connect to the '{wifi_config.value}' network. Please let me know if you need further assistance."
                ai_intent = "get_info"
                ai_entities = {"info_type": "wifi_password"}
                GuestRequest.objects.create(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=raw_text,
                    ai_intent=ai_intent,
                    ai_entities=ai_entities,
                    conci_response_text=conci_response_text,
                    status="completed",
                    timestamp=timezone.now(),
                )
                print(
                    f"Saved GuestRequest for Room {room_number} with intent: {ai_intent} (from direct lookup)"
                )
                return JsonResponse(
                    {
                        "success": True,
                        "response_text": conci_response_text,
                    }
                )
        # --- END OF DIRECT HOTEL INFO LOOKUP ---

        # If not a direct info lookup, proceed with AI processing
        gemini_response_data = call_gemini_api(
            raw_text, room_number=room_number, chat_history=chat_history
        )
        if not gemini_response_data.get("success"):
            print(f"Gemini API call failed: {gemini_response_data.get('error')}")
            return JsonResponse(
                {
                    "success": False,
                    "error": gemini_response_data.get(
                        "error", "Gemini AI processing failed."
                    ),
                },
                status=500,
            )

        ai_intent = gemini_response_data["ai_intent"]
        ai_entities = gemini_response_data["ai_entities"]
        conci_response_text = gemini_response_data["conci_response_text"]

        # --- Conditional Saving/Updating to Database ---
        actionable_intents = [
            "request_amenity",
            "get_info",
            "amenity_request",
            "request_menu",
        ]

        if ai_intent in actionable_intents:
            # Try to find an existing pending request for this room and intent
            # This logic assumes only ONE active request of a given actionable_intent per room at a time.
            # For more complex scenarios (e.g., multiple pending amenity requests), a unique conversation ID
            # would be needed to group related turns.
            existing_request = (
                GuestRequest.objects.filter(
                    hotel=hotel,
                    room_number=room_number,
                    ai_intent=ai_intent,
                    status="pending",
                )
                .order_by("-timestamp")
                .first()
            )  # Get the most recent pending request

            if existing_request:
                # Update existing request
                existing_request.raw_text = (
                    raw_text  # Update with the latest guest query
                )
                existing_request.conci_response_text = (
                    conci_response_text  # Update with the latest Conci response
                )
                existing_request.ai_entities = ai_entities  # Update entities
                existing_request.save()
                print(
                    f"Updated existing GuestRequest (ID: {existing_request.id}) for Room {room_number} with intent: {ai_intent}"  # type: ignore
                )
            else:
                # Create a new request if no matching pending one is found
                status_to_save = "pending"
                if ai_intent == "get_info":
                    status_to_save = "completed"  # Info requests can often be immediately completed if AI handles them

                GuestRequest.objects.create(
                    hotel=hotel,
                    room_number=room_number,
                    raw_text=raw_text,
                    ai_intent=ai_intent,
                    ai_entities=ai_entities,
                    conci_response_text=conci_response_text,
                    status=status_to_save,
                    timestamp=timezone.now(),
                )
                print(
                    f"Created new GuestRequest for Room {room_number} with intent: {ai_intent}"
                )
        else:
            print(
                f"Not saving GuestRequest for Room {room_number}. Intent: {ai_intent}"
            )

        return JsonResponse(
            {
                "success": True,
                "response_text": conci_response_text,
            }
        )

    except Hotel.DoesNotExist:
        return JsonResponse({"success": False, "error": "Hotel not found."}, status=404)
    except Exception as e:
        print(f"Unhandled error in process_guest_command: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": f"An unhandled server error occurred: {str(e)}",
            },
            status=500,
        )
