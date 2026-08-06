"""Trigger the crypto_yield_a2a_orchestrator agent."""

import base64
import threading

from blocks_network import SendMessageRequestPart, create_task_client


def main():
    client = create_task_client()
    session = client.send_message(
        agent_name="crypto_yield_a2a_orchestrator",
        request_parts=[SendMessageRequestPart(
            part_id="request",
            text='{"question":"Give me a combined BTC yield, risk, liquidity, tokenomics, feature, and provenance analysis.","source_file":"yield_data.csv","symbol":"BTC"}',
        )],
    )
    done = threading.Event()

    def on_progress(event):
        print("[progress]", event.get("message") or event.get("progress") or "")

    def on_artifact(event):
        ref = event.artifact_ref
        if ref is None:
            print("[artifact]", event.raw)
        elif ref.kind == "inline" and ref.data:
            print("[artifact]", base64.b64decode(ref.data).decode())
        else:
            print("[artifact]", session.download_artifact(ref).data.decode())

    def on_terminal(event):
        print("[done]", event.state)
        done.set()

    session.on_progress(on_progress)
    session.on_artifact(on_artifact)
    session.on_terminal(on_terminal)
    done.wait(timeout=90)
    session.close()
    client.destroy()


if __name__ == "__main__":
    main()
