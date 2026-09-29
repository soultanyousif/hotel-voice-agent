import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from groq import BadRequestError, Groq

import hotel_db as db

load_dotenv(override=True)
                

MODEL = "qwen/qwen3.8-27b"

if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError(
        "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys, "
        "then put it in a .env file (see .env.example) or set it as an HF Space secret."
    )

client = Groq()

SYSTEM_PROMPT_TEXT = Path(__file__).parent.joinpath("system_prompt.txt").read_text(encoding="utf-8")


def build_system_prompt():
  
    return SYSTEM_PROMPT_TEXT + f"\n\nتاريخ اليوم: {date.today().isoformat()}."


REASONING_EFFORT = {
    "qwen/qwen3.8-27b": "none",
    "qwen/qwen3.6-27b": "none",
    "openai/gpt-oss-120b": "low",
    "openai/gpt-oss-20b": "low",
}


def _extra_params():
    effort = REASONING_EFFORT.get(MODEL)
    return {"reasoning_effort": effort} if effort else {}


PROPOSAL_TOOLS = {"propose_booking"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_room_types",
            "description": "Get all room types with base price and capacity. Use for price or room-type questions when no dates have been given yet.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check which room types have availability for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "description": "Check-in date, YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "Check-out date, YYYY-MM-DD"},
                    "room_type_id": {"type": "integer", "description": "Optional, limit to one room type"},
                },
                "required": ["check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_booking",
            "description": "Check a specific room is available and return the booking details for the guest to confirm. Does not create the booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type_id": {"type": "integer"},
                    "guest_name": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                    "num_guests": {"type": "integer"},
                    "guest_phone": {"type": "string"},
                },
                "required": ["room_type_id", "guest_name", "check_in", "check_out", "num_guests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_booking",
            "description": "Create the booking. Only call this after the guest has explicitly confirmed a proposal from propose_booking in their own reply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type_id": {"type": "integer"},
                    "guest_name": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                    "num_guests": {"type": "integer"},
                    "guest_phone": {"type": "string"},
                },
                "required": ["room_type_id", "guest_name", "check_in", "check_out", "num_guests"],
            },
        },
    },
]

PROPOSAL_MATCH_FIELDS = ["room_type_id", "guest_name", "check_in", "check_out", "num_guests"]


def _matches_last_proposal(confirm_arguments, last_proposal):
    """True only if confirm_booking's arguments are identical, field for field,
    to the arguments of the last successful propose_booking call. This ties a
    confirmation to something the guest was actually shown -- if the details
    changed, or nothing was ever proposed, this returns False."""
    if last_proposal is None:
        return False
    return all(
        confirm_arguments.get(field) == last_proposal.get(field)
        for field in PROPOSAL_MATCH_FIELDS
    )


def run_tool(name, arguments):
    if name == "get_room_types":
        return db.get_room_types()

    if name == "check_availability":
        return db.get_available_rooms(
            arguments["check_in"],
            arguments["check_out"],
            arguments.get("room_type_id"),
        )

    if name == "propose_booking":
        rooms = db.get_available_rooms(
            arguments["check_in"], arguments["check_out"], arguments["room_type_id"]
        )
        if not rooms:
            return {"available": False}
        room = rooms[0]
        return {
            "available": True,
            "room_type_id": room["room_type_id"],
            "name_ar": room["name_ar"],
            "price_per_night": room["price_per_night"],
            "check_in": arguments["check_in"],
            "check_out": arguments["check_out"],
            "num_guests": arguments["num_guests"],
            "guest_name": arguments["guest_name"],
        }

    if name == "confirm_booking":
        booking_id = db.create_booking(
            room_type_id=arguments["room_type_id"],
            guest_name=arguments["guest_name"],
            check_in=arguments["check_in"],
            check_out=arguments["check_out"],
            num_guests=arguments["num_guests"],
            guest_phone=arguments.get("guest_phone"),
        )
        if booking_id is None:
            return {"error": "room no longer available"}
        return {"booking_id": booking_id}

    return {"error": f"unknown tool {name}"}


def to_history_message(message):
   
    entry = {"role": message.role, "content": message.content}
    if message.tool_calls:
        entry["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return entry


class _FallbackMessage:


    role = "assistant"
    content = "عذرًا، صار خلل تقني بسيط. تقدر تعيد كلامك أو سؤالك مرة ثانية؟"
    tool_calls = None


def _completion(messages, tool_choice=None):
   
    kwargs = {"tools": TOOLS}
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=600, **kwargs, **_extra_params()
        )
        return response.choices[0].message
    except BadRequestError as err:
        if "tool_use_failed" not in str(err):
            raise

    messages.append({
        "role": "system",
        "content": (
            "ملاحظة داخلية: محاولة استخدام أداة سابقة فشلت بسبب معلومات ناقصة أو غير صحيحة. "
            "لا تستخدم أي أداة الآن، رد نصي عادي واسأل الضيف عن المعلومة الناقصة إذا كانت لسه ناقصة."
        ),
    })
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=600, **_extra_params()
        )
        return response.choices[0].message
    except BadRequestError as err:
        if "tool_use_failed" not in str(err):
            raise
        return _FallbackMessage()


def agent_turn(messages, last_proposal=None):
    
    message = _completion(messages)

    while message.tool_calls:
        messages.append(to_history_message(message))
        called_propose = False

        for call in message.tool_calls:
            name = call.function.name
            arguments = json.loads(call.function.arguments)

            if name == "confirm_booking" and not _matches_last_proposal(arguments, last_proposal):
                result = {
                    "error": "no matching confirmed proposal - call propose_booking with "
                             "these exact details first and let the guest confirm it"
                }
            else:
                result = run_tool(name, arguments)
                if name == "propose_booking":
                    last_proposal = arguments if result.get("available") else None
                elif name == "confirm_booking" and "booking_id" in result:
                    last_proposal = None  

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
            if name in PROPOSAL_TOOLS:
                called_propose = True

        if called_propose:
            message = _completion(messages, tool_choice="none")
            break

        message = _completion(messages)

    messages.append(to_history_message(message))
    return message.content, messages, last_proposal


if __name__ == "__main__":
    messages = [{"role": "system", "content": build_system_prompt()}]
    last_proposal = None
    print("Type something. Ctrl+C to quit.")
    while True:
        user_text = input("you: ")
        messages.append({"role": "user", "content": user_text})
        reply, messages, last_proposal = agent_turn(messages, last_proposal)
        print("agent:", reply)