import hotel_db as db
from agent import agent_turn, build_system_prompt

db.create_booking(4, "Filler1", "2026-11-01", "2026-11-03", 2)
db.create_booking(4, "Filler2", "2026-11-01", "2026-11-03", 2)

messages = [{"role": "system", "content": build_system_prompt()}]
last_proposal = None
messages.append({
    "role": "user",
    "content": "ابغى احجز الجناح الملكي من 1 لين 3 نوفمبر، الاسم سلطان ورقم 0512345678 لشخصين",
})

before = len(messages)
reply, messages, last_proposal = agent_turn(messages, last_proposal)

for msg in messages[before:]:
    if not isinstance(msg, dict):
        continue
    calls = msg.get("tool_calls")
    if calls:
        for call in calls:
            print("tool call:", call["function"]["name"], call["function"]["arguments"])
    if msg.get("role") == "tool":
        print("  -> result:", msg.get("content"))

print("agent:", reply)