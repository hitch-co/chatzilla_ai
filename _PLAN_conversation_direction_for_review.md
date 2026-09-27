# Conversation direction review plan

## Purpose and timing

Use this plan to review the completed conversation-flow features in the running bot. It contains only behavior that still needs live confirmation. Begin after the OpenAI API migration provides a working request path; some scenarios depend on the migration's final conversation-state design.

Run these checks in a controlled Twitch channel with the normal production configuration. Exercise text delivery first, then repeat audio-dependent scenarios with TTS enabled. Record the observed result and a short failure note beside each scenario. Do not mark a scenario complete from static code inspection alone.

## 1. Viewer greetings and exclusions

- [ ] **G1 — Current viewers only:** Let an eligible viewer appear and leave before the next greeting poll. Confirm the departed viewer is not selected.
- [ ] **G2 — Exact exclusions:** Confirm `cirenexus`, the channel account, configured moderators, and known bots are excluded with mixed-case input.
- [ ] **G3 — Similar names:** Use a viewer name that contains or resembles an excluded name without being equal to it. Confirm the viewer remains eligible.
- [ ] **G4 — Classification:** Confirm eligible first-time and returning viewers still receive the correct new/returning treatment.
- [ ] **G5 — Vibecheck consumers:** Confirm the parsed moderator list also excludes moderators from automatic vibecheck selection.

## 2. Request identity and failure completion

- [ ] **R1 — Current response only:** Arrange an older assistant message followed by a new request. Confirm the request sends only text generated for its own run.
- [ ] **R2 — Shortening identity:** Force a response through shortening. Confirm it shortens the current output using the filled-in original instructions.
- [ ] **R3 — Missing result:** Make the current generation finish without matching assistant text. Confirm the task fails instead of sending an older response.
- [ ] **R4 — Terminal generation failure:** Exercise an unsuccessful terminal model state. Confirm the waiting task receives the exception and does not remain pending.
- [ ] **R5 — Context-write failure:** Exercise a failed message insertion. Confirm the originating task receives the failure.
- [ ] **R6 — Delivery failure:** Exercise a Twitch text-send failure. Confirm requested-reply accounting is released once and later automatic participation is not permanently blocked.

## 3. Text, speech, and shared context

- [ ] **C1 — Text before speech:** Trigger a spoken reply with slow speech generation. Confirm Twitch text appears before speech generation/playback completes.
- [ ] **C2 — Sequential audio:** Confirm speech generation finishes before playback begins and two output tasks do not interleave their audio steps.
- [ ] **C3 — Audio failure after delivery:** Fail speech generation or playback after text is sent. Confirm the text remains delivered and its intended shared-context copy is still queued.
- [ ] **C4 — One shared copy:** Trigger story, explanation, and vibecheck output. Confirm each visible output reaches ordinary conversation context exactly once.
- [ ] **C5 — Same-thread and notice exclusions:** Confirm ordinary `chatformemsgs` output is not copied back into its own thread and command notices are not added as assistant conversation.
- [ ] **C6 — Factcheck source selection:** Provide commands, an earlier factcheck, mirror metadata, and an ordinary factual claim. Confirm factcheck selects the ordinary claim.
- [ ] **C7 — Suppressed generated output:** Start automatic generation, then cause a requested reply or newer qualifying bot reply before automatic delivery. Confirm the automatic text is not sent and the following response does not assume users saw it.

## 4. Automatic conversation direction

- [ ] **D1 — Ordinary activity only:** Send commands, direct bot requests, and bot echoes. Confirm none count toward the ordinary-message threshold.
- [ ] **D2 — Early consideration:** Send two qualifying ordinary messages. Confirm the existing automatic loop wakes and performs one director consideration.
- [ ] **D3 — Fresh input required:** After an ordinary automatic reply, allow the loop to run again without new ordinary input. Confirm `respond` is not delivered.
- [ ] **D4 — Requested reply priority:** Reach the automatic threshold and queue a direct request before automatic output. Confirm the requested reply wins and stale automatic output is suppressed.
- [ ] **D5 — Multiple requested replies:** Queue at least two requested replies. Confirm automatic output stays blocked until both finish, and each request releases the pending count exactly once.
- [ ] **D6 — Inbound-to-queue interval:** Send a direct request while automatic work is near its delivery boundary. Confirm no automatic response slips through before the requested response task becomes pending; record the exact ordering if it does.
- [ ] **D7 — Newer reply invalidates old work:** Begin automatic generation, deliver a newer qualifying bot reply, and confirm the earlier automatic result is discarded.
- [ ] **D8 — Check-in memory:** Allow one `anybody_there` response, then run another consideration without new ordinary input. Confirm it does not repeat. Send new ordinary input and confirm the option becomes eligible again.
- [ ] **D9 — Activity during audio:** Send qualifying ordinary messages while an automatic response is speaking. Confirm the activity is reconsidered after the active run finishes.
- [ ] **D10 — Reset policy:** Confirm ordinary replies and automatic facts/check-ins reset ordinary activity. Confirm story, explanation, vibecheck, greetings, factcheck, `!what`, and command notices do not reset it.
- [ ] **D11 — Quiet schedule:** Leave chat below the wake threshold for the configured interval. Confirm scheduled fact/director behavior still occurs.
- [ ] **D12 — Triggering context order:** Trigger an early director consideration with ordinary messages. Confirm the director sees the messages that caused the wake.

## 5. Personality and retained defaults

- [ ] **P1 — Available choices:** Confirm all thirteen existing archetype names remain loadable.
- [ ] **P2 — Subtle tone:** Sample replies across several archetypes. Confirm wording changes subtly without announcing the archetype, inventing a personal history, or redirecting the topic toward the archetype.
- [ ] **P3 — Timing defaults:** Confirm the active configuration retains story recurrence at 22 seconds, random facts at 500 seconds, greeting polling at 40 seconds, and vibecheck at 5 interactions, 25 words, and a 60-second question interval.

## Review exit criteria

The conversation-direction review is complete when every applicable scenario above has a recorded live result, failures have a small targeted follow-up item, and the suppressed-output scenario confirms that invisible model output cannot affect later visible conversation. Keep API-mechanism findings in `_PLAN_openai_api_update.md`; keep this file centered on user-visible behavior.
