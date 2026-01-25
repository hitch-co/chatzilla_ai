# Threads And Assistants Requirements

## Purpose
Document how assistants and threads are created, how messages flow through them, and the agreed direction for shared context without breaking existing behavior.

## Current Thread Topology (Used In Runtime)
- `chatformemsgs`: primary chat thread for random_fact, chatforme, factcheck, and conversationdirector decisions.
- `ouatmsgs`: story thread for `!startstory`/storyteller flow.
- `explanationmsgs`: explain thread for `!explain`.
- `vibecheckmsgs`: vibecheck thread.

## Current Assistant Usage (Thread Pairing)
- `random_fact` -> `chatformemsgs`
- `chatforme` -> `chatformemsgs`
- `factchecker` -> `chatformemsgs`
- `conversationdirector` -> `chatformemsgs` (function output only)
- `storyteller` -> `ouatmsgs`
- `explainer` -> `explanationmsgs`
- `vibechecker` -> `vibecheckmsgs`
- `newuser_shoutout` -> `chatformemsgs`

## Creation Flow (Where It Happens)
- Assistants are created in `classes/GPTAssistantManagerClass.py` via `create_assistants()` and `create_assistants_with_functions()`.
- Threads are created in `classes/GPTThreadManagerClass.py` via `create_threads()`.
- These are called in `classes/TwitchBotClass.py` inside `event_ready()`.

## Execution Flow (Where Outputs Are Produced)
1) A command or loop enqueues a `CreateExecuteThreadTask`.
2) `classes/TaskManagerClass.py` processes the queue FIFO per thread.
3) `classes/TwitchBotClass.py` handles the task with `handle_tasks()`.
4) `classes/GPTAssistantManagerClass.py` runs the assistant on the thread.
5) Output is sent to Twitch via `ChatForMeService.send_output_message_and_voice()`.
6) Bot output may be mirrored into `chatformemsgs` (see below).

## Mirroring (MC Thread Approach)
Goal: keep `chatformemsgs` aware of bot outputs from other threads so factcheck/randomfact can reference story/explain context.

Current behavior:
- Mirroring happens in `classes/TwitchBotClass.py` after a message is successfully sent.
- This applies to both `execute_thread` and `send_channel_message` tasks.
- Mirroring is skipped if the origin thread is already `chatformemsgs`.
- Mirrored messages are added as `role=assistant` to `chatformemsgs`.
- A verbose tag is prefixed: `origin:<label> | source_thread:<thread> | assistant:<assistant> | <content>`.

Origin label automation:
- Derived from `assistant_name` or `thread_name`.
- Normalized to lowercase, strips `msgs`/`messages`, replaces non-alphanumerics with `_`.
- Always ends in `_agent`.
- No manual mapping tables required.

## Why Keep Separate Threads
- Story/explain/vibecheck loops are long-running and should not crowd normal chat.
- `chatformemsgs` is the master timeline for reactive behavior (random_fact/factcheck/chatforme).
- Mirroring provides shared context with minimal architectural disruption.

## Risks / Tradeoffs
- Mirroring increases token usage in `chatformemsgs`.
- Mirrored content can influence conversationdirector decisions even when no new user messages appear.
- Repeated bot output can still occur if loops fire without new user input.

## Suggested Move-Forward Changes
- Keep the MC-thread mirroring model as default.
- If needed later, add a per-thread toggle for mirroring (opt-in/out per assistant).
- Consider a single global thread only if mirroring proves insufficient or too noisy.
- Keep conversation gating logic (message count since last bot output) so `respond` is only allowed when new user messages exist.
