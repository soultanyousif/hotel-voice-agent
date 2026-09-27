import gradio as gr

from agent import agent_turn, build_system_prompt
from speech import synthesize_speech, transcribe_audio

STATUS_HTML = {
    "idle": """
        <div class="call-status">
            <div class="call-dot" style="background:#9ca3af;"></div>
            <span style="color:#6b7280;">جاهز للتحدث</span>
        </div>
    """,
    "thinking": """
        <div class="call-status">
            <div class="call-dot pulse-slow" style="background:#f59e0b;"></div>
            <span style="color:#b45309;">يفكر...</span>
        </div>
    """,
    "speaking": """
        <div class="call-status">
            <div class="call-dot pulse-fast" style="background:#22c55e;"></div>
            <span style="color:#15803d;">يتكلم...</span>
        </div>
    """,
}

CALL_CSS = """
.call-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 24px;
    font-size: 20px;
}
.call-dot {
    width: 22px;
    height: 22px;
    border-radius: 50%;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(1.35); }
}
.pulse-slow { animation: pulse 1s ease-in-out infinite; }
.pulse-fast { animation: pulse 0.6s ease-in-out infinite; }
#reply_audio { max-height: 40px; opacity: 0.6; }
"""


def start_session():
    agent_messages = [{"role": "system", "content": build_system_prompt()}]
    last_proposal = None
    return agent_messages, last_proposal, STATUS_HTML["idle"]


def handle_turn(audio_path, agent_messages, last_proposal):
    if audio_path is None:
        yield agent_messages, None, last_proposal, STATUS_HTML["idle"]
        return

    yield agent_messages, None, last_proposal, STATUS_HTML["thinking"]

    user_text = transcribe_audio(audio_path)
    agent_messages.append({"role": "user", "content": user_text})

    reply, agent_messages, last_proposal = agent_turn(agent_messages, last_proposal)
    yield agent_messages, None, last_proposal, STATUS_HTML["speaking"]

    reply_audio = synthesize_speech(reply)
    yield agent_messages, reply_audio, last_proposal, STATUS_HTML["idle"]


with gr.Blocks(title="موظف الاستقبال سعودي", css=CALL_CSS) as demo:
    gr.Markdown("<h2 style='text-align:center;'>موظف الاستقبال</h2>")

    status_display = gr.HTML(STATUS_HTML["idle"])

    mic = gr.Audio(sources=["microphone"], type="filepath", label="اضغط وتكلم")
    reply_audio = gr.Audio(elem_id="reply_audio", label=None, show_label=False, autoplay=True)

    agent_state = gr.State([])
    proposal_state = gr.State(None)

    demo.load(start_session, outputs=[agent_state, proposal_state, status_display])

    mic.stop_recording(
        handle_turn,
        inputs=[mic, agent_state, proposal_state],
        outputs=[agent_state, reply_audio, proposal_state, status_display],
    ).then(lambda: None, outputs=mic)


if __name__ == "__main__":
    demo.launch()