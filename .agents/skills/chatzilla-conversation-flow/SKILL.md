---
name: chatzilla-conversation-flow
description: Review or change Chatzilla's Twitch conversation participation, direct-reply priority, automatic director gating, shared model context, response delivery, check-ins, greetings, and personality behavior. Use for conversation-flow tweaks and feature additions in this repository; do not use for unrelated Twitch integration, audio-device setup, data uploads, or the general OpenAI API migration.
---

# Chatzilla conversation flow

Preserve this project's existing classes, queues, task dictionaries, and direct control flow. Make the smallest coordinated change that preserves the invariants below. Read the repository `AGENTS.md`, inspect `git status`, and use `_PLAN_conversation_direction_for_review.md` for the current live-review scenarios.

## Locate the behavior

- `classes/MessageHandlerClass.py` owns bounded recent conversation metadata and counts ordinary user activity separately from the BigQuery upload buffer.
- `classes/TaskManagerClass.py` owns the existing FIFO task queues and the count of requested replies waiting to finish.
- `classes/TwitchBotClass.py` owns event classification, context ordering, director wakeups, automatic-response gates, check-in memory, and successful-send bookkeeping.
- `services/ChatForMeService.py` defines the visible text-delivery boundary and subsequent speech generation/playback.
- `classes/GPTAssistantManagerClass.py` correlates generated text with the request that produced it.
- `config/bot_user_configs/chatzilla_ai.yaml` and the director schema define prompt choices, thresholds, and response vocabulary.

Inspect every caller before changing a return shape, task-dictionary key, counter, or send path. Treat `task_dict` fields as local metadata attached to existing tasks, not an invitation to create another state-management layer.

## Preserve the event order

For an ordinary incoming Twitch message, keep this order:

1. Classify and record the received event locally.
2. Queue its remote conversation-context write before any slow FAISS await can yield.
3. Wake the existing automatic-conversation loop when the ordinary-message threshold is reached.
4. Queue the director decision through the same FIFO scheduler, behind the context writes that triggered it.
5. Recheck automatic-response eligibility immediately before generation and again before visible delivery.
6. On successful text delivery, update conversation activity and reply-version state according to the output type.
7. Generate and play speech sequentially after text is visible.

The queue rule guarantees that the messages which triggered a director decision are ahead of that decision. It does not make every message arriving after director execution begins part of the same decision.

## Preserve the participation rules

- Count ordinary user chat only. Exclude commands, direct requests to the bot, and bot echoes.
- Wake consideration after the configured ordinary-message threshold. A `respond` decision still needs at least one new ordinary user message.
- Keep scheduled quiet-chat facts. Do not turn the director into a viewer-presence or silence state machine.
- Treat `anybody_there_sent` independently from message thresholds. Do not repeat a check-in until new ordinary input clears it.
- Give requested replies priority over automatic output. `pending_requested_replies` is a count because several requests may be queued; each task must release its own pending flag exactly once on successful delivery or scheduler cleanup after failure.
- Use `conversation_reply_count` as a successful bot-reply version. Automatic work snapshots it; a changed value means a newer qualifying bot reply made the automatic result stale.
- Keep the pre-generation gates and the pre-delivery gates. The second check handles changes that occur while the model or speech preparation is awaiting.
- Keep `randomfact_run_in_progress` cleanup in `finally`, and reconsider qualifying activity that arrived while the automatic task was running.

## Treat successful text delivery as the boundary

Update delivered-message state only after Twitch accepts the text. Send text before generating speech so TTS failure cannot erase a response users already saw.

Ordinary conversation replies and automatic facts/check-ins reset ordinary activity. Story, explanation, and vibecheck output may be mirrored into shared conversation context but do not reset ordinary activity. Greetings, command notices, factcheck output, and `!what` output retain their existing reset behavior unless the requested feature explicitly changes it.

Mirror visible output from non-`chatformemsgs` sources into shared conversation context once. Skip same-thread copies and output types that are intentionally excluded. Queue the mirror after successful text delivery and before audio work; do not wait for that queued write from inside the scheduler task that enqueued it.

## Protect request identity and failures

Use the current request/run's assistant text. Never fall back to an older assistant message when the current generation produced no matching text. Shortening must receive the current generated response and the filled-in original instructions.

Every failure path must finish the existing task future with the relevant exception and return. Keep response-task and message-add failures observable. Do not add generalized retry, registry, UUID, TTL, or maintenance machinery.

## Check known timing gaps

- Requested-reply accounting starts when the response task is queued, not at the instant the inbound direct request arrives. Review this small interval when changing inbound awaits or automatic gating.
- Under the old Assistants/Threads flow, an automatic response can be generated and then suppressed locally while its assistant message remains in the remote thread. The OpenAI migration must ensure unseen output does not influence later visible conversation. Keep this case in the review plan.
- A scheduled director run already underway may not include a later-arriving message. Do not promise broader ordering than the FIFO queue provides.

## Make and verify changes

Before editing, write the affected event sequence in terms of inbound event, queued context, director work, requested work, text delivery, shared-context write, and audio. Identify which existing object owns each state value. Change those existing sites together and avoid new classes, managers, schedulers, or persistent state.

When prompts or director decisions change, update the YAML, schema, and all consumers together. Preserve the thirteen archetype names and keep personality as a subtle phrasing cue without announcing an archetype, inventing biography, or steering the topic toward it.

Use static checks appropriate to the files changed: parse Python, YAML, and JSON; run `git diff --check`; review the complete diff and task failure paths. Do not launch the bot, use credentials, or call external services merely to validate a change. Add or update scenarios in `_PLAN_conversation_direction_for_review.md` when live behavior still needs confirmation.
