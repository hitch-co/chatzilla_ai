# Task Update Method Requirements

## Purpose
- Document how tasks are queued and executed today.
- Explain how message metadata is captured for gating.
- Outline gaps and possible changes to align planned responses with task state.

## Current Task Flow
1. Task creation.
   - Producers (TwitchBotClass and services) create AddMessageTask, CreateExecuteThreadTask, or CreateSendChannelMessageTask.
   - Tasks are queued via add_task_to_queue or add_task_to_queue_and_execute.
2. Task queue and scheduler.
   - TaskManager stores per-thread queues in task_queues.
   - task_scheduler loops, pops one task per non-empty queue, and calls _process_task.
3. Task execution.
   - TaskManager._process_task routes tasks into TwitchBotClass.handle_tasks.
   - execute_thread tasks run GPT, optionally send a channel message, and resolve their futures.
   - send_channel_message tasks send text directly.
4. Output mirroring.
   - handle_tasks mirrors bot outputs from non-chatformemsgs threads into chatformemsgs.
   - Mirrored content is added as assistant messages with inline tags (origin/source_thread/assistant).

## Message Capture and Gating
- event_message calls MessageHandler.add_to_appropriate_message_history.
- recent_message_metadata is the rolling buffer used for local gating.
- get_user_message_count_since_last_bot uses is_bot and interaction_type filters.
- randomfact immediate triggers use the message count plus randomfact_immediate_pending.

## Planned Bot Response Marker (current)
- MessageHandler.mark_planned_bot_message adds a synthetic bot record to recent_message_metadata only.
- TwitchBotClass._chatforme_main calls this before enqueuing its task.
- Purpose: reset the "since last bot message" window so randomfact does not fire immediately after a direct mention.

## Gaps / Risks
- Planned markers are not linked to task lifecycle; if a task stalls or fails, gating still behaves as if the bot spoke.
- There is no single view of "pending bot responses" across threads or services.
- Mirrored bot outputs update GPT thread history but not recent_message_metadata unless IRC echo is present.

## Potential Improvements
Option A: TaskManager pending-response registry.
- Add task_id and task_metadata to BaseTask (origin, produces_bot_output, affects_gating).
- TaskManager tracks pending_bot_responses on enqueue and clears on completion/failure.
- Gating checks TaskManager.has_pending_bot_response(...) before triggering randomfact.

Option B: Task lifecycle hooks.
- Add on_task_start/on_task_success/on_task_failure callbacks in TaskManager.
- Use hooks to create and clear planned markers in MessageHandler.
- Use success hooks to confirm bot output when IRC echo is unreliable.

Option C: Centralize message state in MessageHandler.
- Add mark_planned_bot_message(origin, task_id) and mark_confirmed_bot_message(origin, task_id).
- Count planned messages only when a pending task exists in TaskManager.

## Questions / Decisions
- Should planned markers affect gating if a task has not started yet?
- Should non-chatformemsgs outputs reset the "since last bot" window?
- Should mirrored messages carry structured metadata instead of inline tags?

## Suggested Next Steps
- Pick Option A or B to link planned state to task lifecycle.
- Decide whether to count non-chatformemsgs outputs in gating.
- If yes, add MessageHandler hooks when bot outputs are sent or when tasks complete.
