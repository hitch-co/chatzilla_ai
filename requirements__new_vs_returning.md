# New vs Returning Users Service

## Overview
This service polls Twitch chatters and sends a welcome message to new users or a "welcome back" message to returning users, optionally referencing prior chat history from BigQuery + FAISS.

## Activation & Prereqs
- Config gate: `twitch_bot_gpt_new_users_service` must be `True`.
- Ownership gate: `twitch_operator_is_channel_owner` must be `True`.
- Twitch scope: `moderator:read:chatters` (in `twitch_bot_scope`) is required for the chatters API.
- Poll interval: `newusers_sleep_time` controls how often the service checks for new viewers.

## Data Sources
- Twitch API chatters list via `classes/TwitchAPI.py` → `retrieve_active_usernames()`.
- BigQuery:
  - `fetch_unique_usernames_from_bq_as_list()` for historic users at startup.
  - `fetch_user_chat_history_from_bq()` for returning-user context.
- FAISS:
  - `build_and_retrieve_from_faiss_index()` for relevant past messages.
- Known bot list:
  - `data/rules/known_bots.json`.

## Core Flow
1. Startup: `event_ready()` loads `historic_users_at_start_of_session` from BigQuery.
2. Loop: `_send_message_to_new_users_task()` runs every `newusers_sleep_time`.
3. Fetch chatters: `retrieve_active_usernames()` returns current active logins.
4. Classify users: `NewUsersService.get_users_not_yet_sent_message()` compares:
   - Current active users
   - Historic users (BQ)
   - Users already greeted this session (`users_sent_messages_list`)
5. Filter eligible users: exclude known bots, operator, channel, bot identity, moderators.
6. Select one eligible user at random.
7. Returning user path (if `flag_returning_users_service` is `True`):
   - Fetch chat history and `!forget` messages from BQ.
   - Build FAISS query from `newusers_faiss_default_query`.
   - Use `returningusers_msg_prompt` (or fallback) with retrieved context.
8. New user path:
   - Use `newusers_msg_prompt` and a generic context.
9. Send message: create `CreateExecuteThreadTask` targeting `chatformemsgs` with assistant `newuser_shoutout`.
10. Mark greeted: append username to `users_sent_messages_list`.

## Stateful Behavior
- `users_sent_messages_list` persists for the session and prevents repeat greets.
- `historic_users_at_start_of_session` is a snapshot at startup; it is not refreshed mid-session.
- Current active users are evaluated per poll cycle (not cumulative).

## Common Reasons for Sporadic Behavior
- API access: chatters endpoint can return empty/None if scope is missing or the token is invalid.
- Poll timing: `newusers_sleep_time` delays the next greet by design.
- Random selection: only one eligible user is selected per cycle; if the pool is large, a specific user can wait several cycles.
- Task backlog: `TaskManager` queues may delay sending if other tasks are active.
- Returning-user lookup: BigQuery/FAISS latency or errors can slow or break the loop (BQ/FAISS calls are not wrapped in try/except).
- Config gates: if `twitch_operator_is_channel_owner` is False, the service never starts.
- Testing mode: `twitch_bot_faiss_testing_active` forces only the operator to be eligible.
- Moderator list parsing: if moderator names are malformed or not normalized, they can be filtered incorrectly.

## Key Code References
- `classes/TwitchBotClass.py` → `_send_message_to_new_users_task()`
- `services/NewUsersService.py` → `get_users_not_yet_sent_message()`
- `classes/TwitchAPI.py` → `retrieve_active_usernames()`
- `classes/BQUploaderClass.py` → `fetch_unique_usernames_from_bq_as_list()`, `fetch_user_chat_history_from_bq()`
- `services/FaissService.py` → `build_and_retrieve_from_faiss_index()`
- `config/bot_user_configs/chatzilla_ai.yaml` → new user prompts and timers
