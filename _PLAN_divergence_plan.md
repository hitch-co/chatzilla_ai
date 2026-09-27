# Flow-and-prompting reconciliation handoff

## Resume here

- Date: 2026-09-27.
- Investigation and slices 1-5 are implemented in production; slices 1-3 are staged and slices 4-5 remain unstaged. Static validation passed; live verification remains pending.
- This file is the implementation handoff, not authorization to perform the separate API migration.
- Implementation target: `C:\_repos\chatzilla_ai_prod\chatzilla_ai`.
- Candidate source only: `C:\_repos\chatzilla_ai`, including its staged working tree.
- Recommended next step: review slices 4-5 and perform live verification when the bot can run. The separate API migration still requires its own implementation pass.
- Do not merge the feature branch, cherry-pick whole commits, or replace whole files.

## Decisions accepted by the user

1. Production's working tree is authoritative. Reproduce useful feature behavior with small edits to existing functions.
2. Ordinary conversational replies and automatic facts/check-ins reset the ordinary-chat activity count. Story/explanation output remains shared context without resetting that count. Command notices should not reset it.
3. Keep production timing defaults. Shorten archetype descriptions into style cues while retaining existing names and all thirteen choices.
4. Preserve production's explicit `cirenexus` greeting exclusion. This is the conservative interpretation of the user's agreement with the investigation's recommendations; its removal was not explicitly selected.
5. Preserve production bot ears and microphone selection. Do not copy feature's commented-out startup or disabled `!what` response.
6. Preserve useful pending-reply suppression, not the feature's registry/dataclass/UUID/TTL architecture.
7. Reconciliation precedes API migration. Do not redesign code in anticipation of migration.

For output types not explicitly covered above, preserve production command behavior and keep new gating limited to the ordinary conversation flow. Do not silently classify every bot send as a conversational reset.

## Verified repository baseline

Production:

- Branch: `master`.
- HEAD: `d5fc2826d30fcf535ea3f9c40b6c1d4b2f54b2d9`.
- User has now staged all six local changes below. At handoff creation there were no unstaged tracked changes.
  - Added `AGENTS.md`.
  - Added `_PLAN_openai_api_update.md`.
  - Deleted `chatzilla_ai_cirenexus.code-workspace`.
  - Modified `config/startup_audio_devices.py`.
  - Modified `readme/TODO.md`.
  - Modified `run_environment.bat`.
- Preserve these staged changes. In particular, microphone selection is now per launch and is passed through a temporary runtime environment file instead of being persisted to `.env`.

Feature:

- Branch: `flow-and-prompting`.
- HEAD: `e9f4d10290e6338c243a4f785672b0a160e10cb4`.
- Merge base is production HEAD; three feature-only commits, zero production-only commits.
- Commits: `34f884f` (requirements/personality/pacing), `b231b20` (broad conversational work), `e9f4d10` (response selection/message handling).
- Fourteen staged files include pending-response machinery, output-service changes, bot-ears disablement and review documents. No unstaged tracked changes at investigation time.
- `requirements__conversation.md` is deleted in the index but recoverable using `git show HEAD:requirements__conversation.md` in the feature repository.
- Do not alter or clean up the feature repository during implementation.

## Working procedure in production

1. Re-read production `AGENTS.md` and check status/HEAD before editing. If the baseline changed, inspect the difference rather than assuming this inventory is current.
2. Leave the user's existing staged changes intact. Do not reset, stash, stage, or commit them automatically.
3. Leave reconciliation edits unstaged initially. Because the starting production worktree matches its index, `git diff` then isolates new tracked edits from the user's staged baseline; `git diff --cached` shows the baseline separately. Check status for untracked files too.
4. A baseline commit is an optional durable checkpoint for the user; staging alone is not a separate saved revision. It is not a prerequisite to implementing a slice.
5. Inspect feature blocks and their callers as references, then adapt production in place. No bulk file copying or unrelated cleanup.
6. Validate and review each functional slice before broadening the diff. Report what changed and any remaining runtime limitation.
7. Do not add tests. Use static checks and existing safe/local checks only. Do not launch the bot, send messages, use credentials, or call external services merely for validation without authorization for that activity.
8. Update the slice checklist and brief resume notes in this plan as implementation proceeds.

## Implementation slices

### Slice 1: Current-viewer greeting eligibility

Status: Implemented (2026-09-27); static validation passed, live verification pending.

- [x] Replace session-wide greeting candidates with the current successful chatter snapshot.
- [x] Normalize greeting exclusions and use exact username membership, including `cirenexus`.
- [x] Parse comma-separated moderators into trimmed lowercase names and adapt vibecheck exclusions.
- [x] Normalize known-bot names while preserving new/returning classification.
- [x] Parse all three edited Python files and run `git diff --check`; confirm the staged baseline is unchanged.
- [ ] Verify greeting eligibility and vibecheck behavior with the running bot when available.

Validation was static only: no new tests, application imports, bot launch, credentials, or external service calls. Greeting timing, BQ/FAISS behavior (including the operator testing override), and when users are marked greeted remain unchanged.

Goal: greet eligible people currently present, without substring-based identity exclusions.

Files and edits:

- `classes/TwitchBotClass.py`: in `_send_message_to_new_users_task`, use the current successful chatter snapshot instead of accumulating session-wide candidates. Normalize usernames and use exact membership for operator/channel/bot/moderator exclusions. Retain the explicit `cirenexus` exclusion as an exact username exclusion.
- `classes/ConfigManagerClass.py`: parse the comma-separated moderator environment value into individual names in the existing loader.
- `services/NewUsersService.py`: normalize known-bot names to lowercase; preserve the existing new/returning classification.
- `classes/TwitchBotClass.py`: adapt vibecheck moderator exclusions to the parsed list so the config change does not leave a broken consumer.

Dependencies: these identity/config changes travel together. BQ, FAISS, greeting timing, and when users are marked greeted remain unchanged.

Approximate size: 25-50 edited lines.

Later manual verification: departed users are not selected; a username that merely resembles an excluded account remains eligible; known bots and moderators stay excluded; new/returning classification still works.

### Slice 2: Correct response selection and failure delivery

Status: Implemented (2026-09-27); static validation passed, live verification pending.

- [x] Carry run IDs through normal response extraction and shortening; raise when the matching assistant text is missing, without falling back to old output.
- [x] Stop response polling for unsuccessful terminal states or unsupported required action.
- [x] Complete task futures with exceptions and return after failures; fix the unknown-task future target and propagate message-add failures.
- [x] Include the actual message and filled-in original instructions in shortening, including calls without replacement values.
- [x] Add `wordcount_short` for random-fact responses and use `factcheck_voice` for factcheck output.
- [x] Confirm production launch config, parse edited Python and YAML, review both response extraction callers and task failure branches, and run `git diff --check`.
- [ ] Verify response selection, shortening, and task failure delivery with the running bot when available.

`run_chatzilla-ai_prod.bat` reads `config/.env`, which points `CHATZILLA_CONFIG_YAML_FILEPATH` to this production repository's `config/bot_user_configs/chatzilla_ai.yaml`. That is the YAML updated here. The shell variable itself is unset.

Validation was static only: no new tests, application imports, bot launch, credentials, or live service calls. The optional function-call text response path remains unchanged. Message run-ID semantics were checked against the [official OpenAI message reference](https://developers.openai.com/api/reference/resources/beta/subresources/threads/subresources/messages/methods/list).

Goal: a request sends its own generated response, and failures resolve the existing task future correctly.

Files and edits:

- `classes/GPTAssistantManagerClass.py`: carry the run ID from `_run_and_get_assistant_response_thread_messages` into response extraction and both extraction paths in `execute_thread`, including shortening. Do not substitute an older assistant response when the current response is missing.
- Keep terminal unsuccessful run handling local to `_get_response`. Avoid copying the large diagnostics/fallback expansion.
- `classes/TwitchBotClass.py`: correct string arguments to `future.set_exception`, return after failures, fix the unknown-task future target, and propagate message-add failures rather than claiming success.
- `config/bot_user_configs/chatzilla_ai.yaml`: give shortening the actual message and original instructions. Confirm the launch-time config location before assuming this tracked YAML is the active file.
- Add the missing `wordcount_short` replacement where random-fact response prompts require it.
- Use production's existing `factcheck_voice` config attribute for factcheck output instead of renaming that attribute across files.

Dependencies: run-ID return shape and all relevant callers must change together. The optional function-call text response path is not used by the runtime director caller; do not expand it unnecessarily.

Approximate size: 60-120 edited lines if kept selective.

Later manual verification: no stale reply is sent; shortening uses the intended response; failed generation completes the waiting task with an exception.

Migration constraint: these old run/thread mechanics overlap heavily with the next project. If reported startup failure prevents live verification, record that limitation instead of adding more retries or claiming runtime success.

### Slice 3: Prompt text delivery and shared context

Status: Implemented (2026-09-27); static validation passed, live verification pending.

- [x] Send text before speech generation; await generation and playback sequentially through `asyncio.to_thread`.
- [x] Pass the source thread through both output-task paths; enqueue an assistant-context copy after successful chat delivery for non-`chatformemsgs` output.
- [x] Skip same-thread copies and ordinary command notices; preserve story/explanation/vibecheck threads and existing bot-echo exclusions.
- [x] Queue shared context before audio starts so later audio failure does not discard it.
- [x] Guide factcheck claim selection to ignore command text, previous factchecks, and mirror metadata.
- [x] Parse edited Python and YAML, review callers and scheduler ordering, and run `git diff --check`.
- [ ] Verify shared context appears once, speech remains sequential, and audio failure leaves delivered text available as context with the running bot.

Mirroring uses the existing `AddMessageTask` queue with `source_thread:` metadata and assistant role. It is enqueued immediately after text delivery and inserted remotely when the scheduler reaches it, after the current output task finishes or fails. The send wrapper must not wait for that queued task from inside the same scheduler. Existing queued work retains its order; the director's separate execution and its context-ordering work remain for slice 4.

Validation was static only: no new tests, application imports, bot launch, credentials, live service calls, or audio playback. The active production YAML was reconfirmed through the launch configuration. All earlier work was staged before slice 3 edits began; the staged baseline was preserved.

Goal: text reaches chat without waiting for speech generation; other bot activities contribute visible output to ordinary-chat context.

Files and edits:

- `services/ChatForMeService.py`: in `send_output_message_and_voice`, send text first, then await speech generation and playback through `asyncio.to_thread`, sequentially. Do not add feature's task UUID plumbing.
- `classes/TwitchBotClass.py`: mirror visible outputs from non-`chatformemsgs` threads into `chatformemsgs` as assistant context. Skip same-thread output to avoid duplication.
- Align mirroring/confirmation with successful text delivery so subsequent audio failure does not erase the fact that chat saw the message.
- Preserve the existing separate story/explanation/vibecheck threads. A small existing-class helper for mirroring is sufficient.
- Port factcheck prompt guidance to ignore command text, earlier factcheck output and mirror tags when selecting a claim.

Dependencies: slice 2 response correlation prevents mirrored assistant messages from being mistaken for current generated output. Coordinate remote message insertion with existing task ordering; do not create another scheduler.

Approximate size: 35-70 edited lines plus prompt text.

Later manual verification: story/explanation text is visible to ordinary-chat context once; audio remains sequential; text is already delivered if later audio work fails.

### Slice 4: Ordinary-conversation participation

Status: Implemented (2026-09-27); static validation passed, live verification pending.

- [x] Keep bounded ordinary-chat activity separate from the BQ upload buffer; exclude commands, direct requests, and bot echoes from ordinary-user counting.
- [x] Wake the existing random-fact loop after two ordinary messages, requiring at least one for `respond`; preserve scheduled quiet-chat posting and adjustable timing.
- [x] Queue director decisions behind incoming/shared context in the existing scheduler, using `BaseTask` rather than a new task class or scheduler.
- [x] Add `anybody_there` to the schema and prompts; remember actual check-ins until new ordinary input, independently of message-count thresholds.
- [x] Track queued requested replies with a count and per-task flag; suppress automatic generation/delivery while they are pending and release once on send or scheduler cleanup.
- [x] Append qualifying bot sends at actual text-delivery time. Only ordinary replies and automatic facts/check-ins reset the activity count; story/explanation/vibecheck output, greetings, factcheck/what output, and command notices do not.
- [x] Skip automatic output superseded by a delivered requested reply; clear run state in `finally` and reconsider new ordinary activity received during audio playback.
- [x] Parse edited Python/YAML/JSON, review queue and send/failure paths, and run `git diff --check`.
- [ ] Verify participation, multiple pending requests, send failures, speech-time activity, and shared-context ordering with the running bot.

Implementation notes: the wake event interrupts the existing adjustable sleep without changing its configured interval. Requested-reply accounting begins when the `!chat`/direct-mention, `!what`, or factcheck response task is queued. Existing command preparation remains unchanged. Incoming context is queued before FAISS work can yield; user activity is recorded on receipt, while bot activity is recorded only after successful text delivery. BQ/FAISS history and inbound-echo storage remain intact. Director execution now uses the same queue as context writes. The existing function-call cancellation mechanics remain unchanged for migration.

The main loop diff includes indentation under a local `try`/`finally` so errors cannot leave it marked active. Small additions to `TaskManagerClass.py`, `ChatForMeService.py`, and `adjustable_sleep_task.py` carry the existing task dictionary to successful-send bookkeeping, release pending counts, and wake the existing timer. No new tests, classes, registries, IDs, TTLs, or maintenance loops were added.

Goal: consider responding after ordinary user activity, avoid replying again to unchanged conversation, and prioritize already-requested replies.

Files: `classes/MessageHandlerClass.py`, `classes/TwitchBotClass.py`, `classes/ConfigManagerClass.py`, bot YAML, director schema, and only minimal task bookkeeping if necessary.

Keep:

- A bounded recent-message buffer separate from the BQ upload buffer, which is cleared frequently.
- Ordinary user-message counting, excluding commands and bot output.
- Earlier consideration after two qualifying messages and a minimum of one new user message for `respond`.
- Director decisions `respond`, `fact`, and `anybody_there`, with matching prompts/schema and prevention of repeated check-ins without new input.
- Priority for direct requested replies, using the existing direct-mention/command routes.

Implement conservatively:

- Record actual qualifying bot sends in chronological order. Do not replace a task-start placeholder in an older list position.
- Keep pending requested replies distinct from actual chat messages. Consider a small pending count and per-task release flag within existing task dictionaries/functions; account for multiple queued requests and release exactly once on send/failure. This is an implementation candidate, not a requirement to introduce a new tracking layer.
- Do not add UUIDs, a pending-response class/registry, TTLs, lifecycle callbacks, or a maintenance loop.
- Ensure timer/run-state cleanup executes on failure as well as success, using local `finally` handling.
- Do not couple check-in memory size to the incoming-message threshold.
- Ensure an immediate director decision does not run before its triggering messages have reached the context it reads. Reuse existing queue/completion mechanisms where practical.
- Use the accepted reset policy above. Do not let generic send-wrapper bookkeeping make story output or command notices reset the ordinary-chat counter.
- Avoid counting local confirmation and an inbound echo as two separate bot outputs. Keep any echo handling narrowly scoped to local gating; do not remove BQ/FAISS history paths without evidence.

Dependencies: correct response delivery, ordering, and actual-send confirmation. Preserve existing scheduled posting to quiet chat; this slice does not introduce a viewer-presence gate or silence policy.

Approximate size: 100-200 edited lines, subject to preserving existing control flow.

Later manual verification: commands do not count; ordinary activity triggers one consideration; requested replies suppress automatic participation; send/failure releases pending state; normal sleep is restored; story/explanation output does not reset the ordinary conversation count.

### Slice 5: Minimal personality refinement

Status: Implemented (2026-09-27); static validation passed, live tone verification pending.

- [x] Shorten all thirteen production archetypes to style cues, preserving every key and its order.
- [x] Add subtle tone guidance to the shared assistant suffix; retain the existing no-archetype-announcement instruction and reinforce it in the suffix.
- [x] Confirm production defaults remain unchanged: story 22 seconds, facts 500 seconds, greetings 40 seconds, vibecheck 5 interactions / 25 words / 60 seconds.
- [x] Parse the JSON/YAML and compare archetype keys and timing values against the staged baseline.
- [ ] Verify tone stays subtle in live replies.

Goal: personality influences phrasing without dragging replies into invented biographical topics.

- `data/bot_archetypes/bot_archetypes.json`: shorten descriptions to style cues while retaining all thirteen production keys/options.
- Bot YAML: selectively adopt subtle-personality guidance without dropping the existing instruction not to announce the archetype.
- Keep production timing defaults: story 22 seconds, random facts 500 seconds, greeting polling 40 seconds; vibecheck 5 interactions, 25 words, 60-second question interval.
- Leave unused-setting cleanup and `assistant_model_davinci` renaming out of scope.

Dependencies: none beyond existing prompt loading. Small data/prompt diff.

Later manual verification: original archetype choices remain available and tone stays subtle.

## Known implementation traps and evidence

- `b231b20` calls message-handler methods added only in `e9f4d10`; do not cherry-pick the earlier commit as an independent feature.
- Feature confirmed-marker replacement preserves task-start position, so messages received during generation remain after the apparent bot response in the local list.
- Confirmation without a task ID can replace another task's latest planned marker.
- Feature TTL expiry releases gating without cancelling the work, allowing a late reply after expiry.
- The director calls the API outside TaskManager's queue. Immediate triggering amplifies the risk of reading context before queued user messages arrive.
- Feature mirroring follows the complete text/audio service call, so audio failure can prevent mirroring already-visible text.
- Feature HEAD records confirmed output in more than one place; staged work centralizes that, but inbound echo duplication remains unresolved.
- New-user notes incorrectly place the greeted-list update after sending; actual code marks the selected user before retrieval/send. Do not silently broaden slice 1 to fix that pre-existing behavior.
- `GPTThreadManager` is defined inside `classes/GPTAssistantManagerClass.py`; the documentation's separate-file reference is stale.

## Migration handoff and validation limits

Production's separate `_PLAN_openai_api_update.md` reports startup `openai.NotFoundError: 404` at assistant creation. The reconciliation investigation did not make an API call to verify that claim.

Treat production as the authoritative code baseline, not proof that its external API still runs today. Reconciliation can establish a reviewable code state; live restoration/verification may have to wait for migration. Do not merge the two projects or build new API architecture during reconciliation.

Preserve these behavioral requirements for migration:

- Current-request response identity, including shortening.
- Correct failure completion of task futures.
- Director decision vocabulary and local participation gates.
- Shared output context without duplication.
- Ordering of incoming context, decisions, text delivery and audio completion.

Run polling, run IDs, thread-busy retries, remote assistant-message mirroring, and function required-action/cancellation mechanics are the main overlap. They are mechanisms, not requirements for the future API.

Static Python parsing and tracked bot-YAML parsing passed in both repositories during investigation. No application imports, bot launch, live API calls, or new tests were used. The shell did not define `CHATZILLA_CONFIG_YAML_FILEPATH`; verify the real launch configuration without displaying credentials.

## Resume notes

- Completed: investigation and slices 1-5 in production. Python/YAML/JSON parsing and diff whitespace checks passed; all thirteen archetype keys and production timing defaults were verified against the index. Slices 1-3 were staged before slices 4-5 began; that staged baseline remains unchanged. Slices 4-5 code, prompts, data, and plan updates remain unstaged.
- Pending manual verification: departed viewers disappear from greeting candidates; similar usernames remain eligible; mixed-case known bots/moderators are excluded; new/returning classification and automatic vibecheck exclusions work as intended. Live startup may remain blocked by the separately reported API issue.
- Pending slice 2 manual verification: a request sends only its own response, shortening selects its own run's text, and failed generation/message insertion/delivery resolves the waiting task with an exception. No live startup attempt was made.
- Pending slice 3 manual verification: shared story/explanation/vibecheck context appears once, text precedes speech, audio stays sequential, and an audio failure does not discard the queued shared context.
- Pending slices 4-5 manual verification: ordinary activity triggers consideration, pending requested replies suppress automatic output, send/failure releases counts once, check-ins do not repeat without new input, story/explanation output does not reset activity, and archetype tone stays subtle.
- Validation remained static: no new tests, application imports, bot launch, credentials, live API calls, or audio playback.
- Not started: API migration.
- Next action: review the unstaged slices 4-5 diff. Live verification may need to wait for the separate API migration. Preserve the current staged and unstaged work when beginning that migration.
