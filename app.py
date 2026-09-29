# import gradio as gr

# from agent import agent_turn, build_system_prompt
# from speech import synthesize_speech, transcribe_audio

# STATUS_HTML = {
#     "idle": """
#         <div class="call-status">
#             <div class="call-dot" style="background:#9ca3af;"></div>
#             <span style="color:#6b7280;">جاهز للتحدث</span>
#         </div>
#     """,
#     "thinking": """
#         <div class="call-status">
#             <div class="call-dot pulse-slow" style="background:#f59e0b;"></div>
#             <span style="color:#b45309;">يفكر...</span>
#         </div>
#     """,
#     "speaking": """
#         <div class="call-status">
#             <div class="call-dot pulse-fast" style="background:#22c55e;"></div>
#             <span style="color:#15803d;">يتكلم...</span>
#         </div>
#     """,
# }

# CALL_CSS = """
# .call-status {
#     display: flex;
#     align-items: center;
#     justify-content: center;
#     gap: 12px;
#     padding: 24px;
#     font-size: 20px;
# }
# .call-dot {
#     width: 22px;
#     height: 22px;
#     border-radius: 50%;
# }
# @keyframes pulse {
#     0%, 100% { opacity: 1; transform: scale(1); }
#     50% { opacity: 0.4; transform: scale(1.35); }
# }
# .pulse-slow { animation: pulse 1s ease-in-out infinite; }
# .pulse-fast { animation: pulse 0.6s ease-in-out infinite; }
# #reply_audio { max-height: 40px; opacity: 0.6; }
# """


# def start_session():
#     agent_messages = [{"role": "system", "content": build_system_prompt()}]
#     last_proposal = None
#     return agent_messages, last_proposal, STATUS_HTML["idle"]


# def handle_turn(audio_path, agent_messages, last_proposal):
#     if audio_path is None:
#         yield agent_messages, None, last_proposal, STATUS_HTML["idle"]
#         return

#     yield agent_messages, None, last_proposal, STATUS_HTML["thinking"]

#     user_text = transcribe_audio(audio_path)
#     agent_messages.append({"role": "user", "content": user_text})

#     reply, agent_messages, last_proposal = agent_turn(agent_messages, last_proposal)
#     yield agent_messages, None, last_proposal, STATUS_HTML["speaking"]

#     reply_audio = synthesize_speech(reply)
#     yield agent_messages, reply_audio, last_proposal, STATUS_HTML["idle"]


# with gr.Blocks(title="موظف الاستقبال سعودي", css=CALL_CSS) as demo:
#     gr.Markdown("<h2 style='text-align:center;'>موظف الاستقبال</h2>")

#     status_display = gr.HTML(STATUS_HTML["idle"])

#     mic = gr.Audio(sources=["microphone"], type="filepath", label="اضغط وتكلم")
#     reply_audio = gr.Audio(elem_id="reply_audio", label=None, show_label=False, autoplay=True)

#     agent_state = gr.State([])
#     proposal_state = gr.State(None)

#     demo.load(start_session, outputs=[agent_state, proposal_state, status_display])

#     mic.stop_recording(
#         handle_turn,
#         inputs=[mic, agent_state, proposal_state],
#         outputs=[agent_state, reply_audio, proposal_state, status_display],
#     ).then(lambda: None, outputs=mic)


# if __name__ == "__main__":
#     demo.launch()
import base64
from pathlib import Path

import gradio as gr

from agent import agent_turn, build_system_prompt
from speech import synthesize_speech, transcribe_audio

BASE_DIR = Path(__file__).parent

# Put the avatar image next to app.py. Both file names are checked.
AVATAR_NAMES = ["Saudi_man_emoji.png", "Saudi man emoji.png"]


def load_avatar():
    for name in AVATAR_NAMES:
        path = BASE_DIR / name
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            return f"data:image/png;base64,{data}"
    return ""


AVATAR_SRC = load_avatar()
AVATAR_TAG = f'<img class="avatar" src="{AVATAR_SRC}" alt="">' if AVATAR_SRC else '<div class="avatar"></div>'


def call_screen(state):
    """state is one of: idle, thinking, speaking. The CSS shows the matching label."""
    return f"""
    <div class="call-screen state-{state}">
        <div class="call-top">مكالمة جارية</div>
        <div class="avatar-wrap">
            <div class="ring ring-1"></div>
            <div class="ring ring-2"></div>
            {AVATAR_TAG}
        </div>
        <div class="call-name">موظف استقبال سعودي</div>
        <div class="call-state">
            <span class="lbl lbl-idle">في انتظارك</span>
            <span class="lbl lbl-thinking">يفكر...</span>
            <span class="lbl lbl-speaking">يتكلم...</span>
        </div>
    </div>
    """


def audio_player(path):
    """Embed the reply audio directly in the page so it always starts from the
    beginning and plays automatically. When it ends, the screen goes back to idle."""
    data = base64.b64encode(Path(path).read_bytes()).decode()
    back_to_idle = "document.querySelector('.call-screen').className='call-screen state-idle';"
    return (
        f'<audio autoplay src="data:audio/wav;base64,{data}" '
        f'onended="{back_to_idle}" onerror="{back_to_idle}"></audio>'
    )


CALL_CSS = """
:root, .gradio-container {
    --body-background-fill: #0b0f14;
    --background-fill-primary: #121821;
    --background-fill-secondary: #121821;
    --block-background-fill: #121821;
    --block-border-color: #1f2937;
    --body-text-color: #e5e7eb;
    --block-label-text-color: #9ca3af;
    --border-color-primary: #1f2937;
}
body, .gradio-container {
    background: #0b0f14 !important;
    color: #e5e7eb !important;
}
.gradio-container {
    max-width: 420px !important;
    margin: 0 auto !important;
    padding: 12px !important;
}
footer { display: none !important; }

.call-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 28px 16px 20px 16px;
    min-height: 470px;
    border-radius: 28px;
    background: linear-gradient(180deg, #16202e 0%, #0b0f14 100%);
    border: 1px solid #1f2937;
    color: #e5e7eb;
}
.call-top { font-size: 14px; color: #9ca3af; }
.avatar-wrap {
    position: relative;
    width: 200px;
    height: 200px;
    margin: 30px 0 10px 0;
}
.avatar {
    position: absolute;
    inset: 0;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    object-fit: cover;
    background: #e5e7eb;
    border: 3px solid #2b3648;
}
.ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2px solid #22c55e;
    opacity: 0;
}
.call-name { font-size: 24px; font-weight: 700; }
.call-state { font-size: 17px; min-height: 26px; }
.lbl { display: none; }
.state-idle .lbl-idle { display: inline; color: #9ca3af; }
.state-thinking .lbl-thinking { display: inline; color: #f59e0b; }
.state-speaking .lbl-speaking { display: inline; color: #22c55e; }

@keyframes ring-out {
    0% { transform: scale(1); opacity: 0.6; }
    100% { transform: scale(1.5); opacity: 0; }
}
@keyframes breathe {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.04); }
}
.state-speaking .ring { animation: ring-out 1.4s ease-out infinite; }
.state-speaking .ring-2 { animation-delay: 0.7s; }
.state-thinking .avatar { animation: breathe 1.2s ease-in-out infinite; }
.state-thinking .ring { border-color: #f59e0b; }

#mic_box { margin-top: 8px; }
#hidden_player { height: 0; overflow: hidden; padding: 0; border: none; min-height: 0; }
"""


def start_session():
    agent_messages = [{"role": "system", "content": build_system_prompt()}]
    last_proposal = None
    return agent_messages, last_proposal, call_screen("idle"), ""


def handle_turn(audio_path, agent_messages, last_proposal):
    if audio_path is None:
        yield agent_messages, last_proposal, call_screen("idle"), ""
        return

    yield agent_messages, last_proposal, call_screen("thinking"), ""

    user_text = transcribe_audio(audio_path)
    agent_messages.append({"role": "user", "content": user_text})

    reply, agent_messages, last_proposal = agent_turn(agent_messages, last_proposal)

    reply_path = synthesize_speech(reply)
    # The screen stays in the speaking state until the audio element finishes.
    yield agent_messages, last_proposal, call_screen("speaking"), audio_player(reply_path)


with gr.Blocks(title="موظف استقبال سعودي", css=CALL_CSS) as demo:
    status_display = gr.HTML(call_screen("idle"))

    mic = gr.Audio(
        sources=["microphone"],
        type="filepath",
        label="اضغط وتكلم",
        elem_id="mic_box",
    )
    player = gr.HTML("", elem_id="hidden_player")

    agent_state = gr.State([])
    proposal_state = gr.State(None)

    demo.load(start_session, outputs=[agent_state, proposal_state, status_display, player])

    mic.stop_recording(
        handle_turn,
        inputs=[mic, agent_state, proposal_state],
        outputs=[agent_state, proposal_state, status_display, player],
    ).then(lambda: None, outputs=mic)


if __name__ == "__main__":
    demo.launch()