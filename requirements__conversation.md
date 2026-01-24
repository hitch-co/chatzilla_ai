# Conversation Poll Requirements

## Background
- Repeated or near-duplicate bot replies are showing up in the live chat flow.
- Current conversation state is split across multiple places (thread history, in-memory histories, FAISS).
- We want lightweight, local signals that help decide when the bot should speak without changing core behavior yet.

## Goal
Provide a small "conversation poll" snapshot that can be used to decide whether the bot should respond, based on what happened since the bot last spoke.

## Non-Goals (for this phase)
- No new persistence layer.
- No deep semantic moderation or full conversation summarization.
- No changes to bot prompts or response text in this phase.

## Current Flow Notes (How Messages Move Today)
- `event_message` calls `_get_message_metadata`, then `add_to_appropriate_message_history` for every message.
- `message_history_raw` is cleared after BQ upload when it has 2+ messages, so it is not a stable window.
- `all_msg_history_gptdict` keeps GPT-ready strings, but does not preserve metadata fields.
- `add_to_thread_history` only queues non-bot authors; bot output is not added to the thread here.
- Bot output is sent through `_send_channel_message_wrapper`; it only re-enters `event_message` if Twitch IRC echoes bot messages and TwitchIO dispatches them (no explicit in-app reinsert, `message.echo` is not checked).
- `users_in_messages_list_text` is cumulative for the session and not pruned to a recent window.

## Rolling Buffer (Required)
- Add a `recent_message_metadata` list (or similar) that stores raw metadata for the last N messages.
- Append every inbound message after `_get_message_metadata`.
- Append bot outputs at send time with a lightweight metadata record (`source='local_send'`, `role='assistant'`, `name=twitch_bot_username`).
- Keep size limited by a new `conversation_poll_window_size` (default to `msg_history_limit` or smaller).
- Use this buffer to compute "since last bot message" slices and timestamps.
Config keys (proposed):
- `conversation_poll_window_size`
- `qualifying_command_threshold`
- `qualifying_command_window_seconds`
- `randomfact_sleeptime_default`

## Proposed Snapshot (Since Last Bot Message)
- last_bot_message_id
- last_bot_message_timestamp
- last_bot_message_source (twitch_event, local_send, thread_only)
- last_bot_message_origin (randomfact, chatforme, command, system)
- messages_since_last_bot_count
- unique_users_since_last_bot_count
- per_user_message_counts (since last bot message)
- messages_with_bot_mention_count
- command_message_count
- last_command_timestamp (optional)
- last_command_name (optional, parsed from leading token)
- time_since_last_bot_message_seconds
- recent_messages_sample (last N user messages, optional)

## Data Inputs (From Existing Metadata)
Use fields already present in message metadata:
- name, user_id, display_name
- channel, timestamp
- content (already cleaned by command spellcheck)
- role, interaction_type
- message_id
Notes:
- Bot messages will show up as `role='user'` if `event_message` receives them, so role alone is not enough.
- `interaction_type` marks bot mentions as `command`, so bot mention counts should not rely on command filtering alone.

## Decisions (Current)
- Use a rolling buffer of raw message metadata for poll computation.
- Commands do not count toward general activity, but bot mentions inside commands still count as high-priority signals.
- Poll gating applies to chatforme/randomfact only; long-form sessions (story/explain/factcheck) continue unless explicitly coordinated.
- No multi-channel behavior is required.
- Qualifying commands trigger an "immediate" next scheduled chatforme/randomfact run (single-shot flag, still subject to gate checks).
- Add a configurable threshold for qualifying commands (minimum count within a time window) in `config/bot_user_configs/chatzilla_ai.yaml`, loaded by `classes/ConfigManagerClass.py`.
- After an immediate run, reset any temporarily shortened sleep time back to the default YAML value.

## Decision Examples (Downstream Usage + Alternatives)
- If unique_users_since_last_bot_count >= 2, do not interject.
- If one user has >= 2 messages since last bot message, consider replying only if asked or tagged.
- If messages_with_bot_mention_count >= 1, prioritize a reply.
- If time_since_last_bot_message_seconds > randomfact_sleeptime, allow a reply unless chat is active.
- If a qualifying command arrives (e.g., !factcheck, !startstory), set an immediate-next-run flag for chatforme/randomfact (one-shot), still subject to the gate.
 - If the immediate-next-run path shortens `randomfact_sleeptime`, restore it to the default after the run.
Operational detail:
- Commands (messages starting with "!") should not increase general activity counts, but bot mentions within those commands should still increment `messages_with_bot_mention_count`.
Alternatives / tradeoffs:
- Use a simple activity score (unique_users * message_count) instead of hard gates.
- Permit a response when chat is active but bot was directly mentioned or asked a question.
- Apply softer rules for randomfact vs. direct mentions (separate thresholds).
- Use a time-based cool-down plus a short recent-message window rather than a hard count.

## Open Questions
- What counts as a "bot message"? (assistant role only, bot username only, or any message sent by the bot process)
  - This needs a full evaluation of pros/cons. Assistant role is tricky because threads can be long-lived. Bot-username-only is simpler but can miss edge cases. Any message sent by the bot process is most robust but may be overkill for now.
- Should messages from the streamer/mods/bots be excluded from unique user counts?
  - Leaning no, but a future toggle for mod exclusion could be useful.
- What happens if the last bot message is not in the in-memory window (history limit)?
  - This needs a clear decision: keep a dedicated rolling buffer, or accept "unknown" and default to safe behavior.
- Should the snapshot reset on any bot output, or only on certain message types (chat vs. system)?
  - Similar to the assistant-role issue; needs a decision on what output types reset the poll.
- Do we want a simple dedupe check on recent bot outputs to reduce near-repeats?
  - Leaning no: GPT outputs vary slightly and we do not want FAISS-based dedupe here.
- Should we treat commands containing bot mentions as a separate signal (mention + command) for priority replies?
- Which command types should reduce scheduled chat delay (all commands, only content-creation commands, or only direct mentions)?
- What is the intended "threshold rule" before the immediate-next-run flag is allowed (count threshold, cool-down, or per-command allowlist)?

## Code References (Existing Touchpoints)
- `classes/MessageHandlerClass.py` (message metadata, in-memory histories, message_id, add_to_thread_history)
- `classes/TwitchBotClass.py` (event_message flow, handle_tasks, randomfact_task, _chatforme_main, _send_channel_message_wrapper)
- `classes/TaskManagerClass.py` (task queues, execution timing)
- `models/task.py` (AddMessageTask, CreateExecuteThreadTask, CreateSendChannelMessageTask)
- `classes/GPTAssistantManagerClass.py` (thread messages and assistant responses)
- `services/FaissService.py` (session index for chat history)
- `services/VibecheckService.py` (uses all_msg_history_gptdict)
- `services/ChatForMeService.py` (bot output delivery)
- `services/ExplanationService.py` (repeat output loop via task queue)
- `config/bot_user_configs/chatzilla_ai.yaml` (msg_history_limit, randomfact_sleeptime, prompt guidance)
- `classes/ConfigManagerClass.py` (loads msg_history_limit, randomfact config)
- `my_modules/adjustable_sleep_task.py` (scheduled timing for randomfact and other loops)

## Assistant Coordination Options (Non-Gating)
- Priority bands: allow randomfact/chatforme to coexist, but de-prioritize bot responses when a long-form assistant (story/explain) is active.
- Cooldowns by assistant type: short cooldowns for chatforme, longer for randomfact, none for story/explain unless explicitly stopped.
- Topic ownership: when a long-form session starts, annotate a "current topic" and let chatforme only answer direct mentions or questions.
- Soft arbitration: if two assistants are scheduled within a short window, prefer the one that is user-triggered (command/mention) over scheduled.

## Future Options (Post-MVP)
- Light semantic summarization or topic drift detection to reduce "repeat-ish" replies.
- Optional per-user thread summaries (low-cost) to avoid repeating advice to the same chatter.
