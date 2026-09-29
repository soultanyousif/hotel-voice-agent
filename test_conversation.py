from agent import agent_turn, build_system_prompt

conversation = [
    "السلام عليكم، أبغى أحجز غرفة",
    "أنا اسمي سلطان",
    "من 6 لين 8 اكتوبر",
    "كم سعر الغرفة الديلوكس؟",
    "شخصين",
    "ايوه",
    "ايوه اكده",
    "لا شكرا",
]

messages = [{"role": "system", "content": build_system_prompt()}]
last_proposal = None

for turn in conversation:
    messages.append({"role": "user", "content": turn})
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

    print("you:", turn)
    print("agent:", reply)
    print()