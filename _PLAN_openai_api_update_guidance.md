# FYI / IMPLEMENTATION CONTEXT — OPENAI API MIGRATION

Use the existing `*PLAN.md` / `OPENAI_MIGRATION_PLAN.md` as the authoritative implementation plan.

**Do not replace, rewrite, reinterpret, or expand the plan into a different architecture based on this document.**

This document exists to provide additional context about the current OpenAI API landscape, likely migration differences, implementation nuances, and things to watch for while executing the existing plan.

The hierarchy is:

```text
1. Existing migration PLAN.md
   = scope, milestones, sequencing, project philosophy

2. Actual repository code
   = source of truth for how Chatzilla currently works

3. Current official OpenAI documentation
   = source of truth for how the API works now

4. These notes
   = implementation context and cautions
```

If these notes describe a pattern that does not exist in the repository, ignore that pattern.

**Do not reshape the repository to make it look like these examples.**

Discover the existing implementation first and adapt it as narrowly as possible.

---

# 1. DO NOT GUESS THE APPLICATION ARCHITECTURE

This is especially important.

Do not infer that Chatzilla has a particular:

- Assistant lifecycle
- Thread lifecycle
- Conversation lifecycle
- request object hierarchy
- queue implementation
- tool registry
- prompt registry
- state manager
- context manager
- persistence mechanism
- streaming architecture
- retry mechanism
- async topology

simply because old or new OpenAI documentation shows one.

Inspect the actual code.

Examples in this document are **API illustrations**, not descriptions of the repository.

Wherever implementation depends on something such as:

```text
how assistant configurations are stored
how requests are routed
how context is constructed
whether threads were reused
whether tools actually execute Python
whether output is streamed
whether response IDs are retained
whether model calls are already async
```

find the answer in the repo before changing anything.

The objective remains:

> Adapt the existing application to the current OpenAI API with the smallest understandable changes.

---

# 2. CURRENT OPENAI BASELINE

As of September 27, 2026, the old Assistants API is no longer merely deprecated.

It was shut down on August 26, 2026.

Calls such as:

```python
client.beta.assistants.create(...)
```

are therefore not something we can repair by updating a parameter or changing a model name.

The supported direction is the **Responses API**.

That means some migration work is syntactic, but some old concepts no longer have a direct runtime object with the same lifecycle.

Do not approach this as:

```text
Assistant → rename to NewAssistant
Thread    → rename to NewThread
Run       → rename to NewRun
```

The lifecycle model changed.

---

# 3. BE CAREFUL WITH OLD ASSISTANTS → PROMPTS MIGRATION GUIDANCE

OpenAI's Assistants migration material may show a conceptual mapping resembling:

```text
Assistant → Prompt
Thread    → Conversation
Run       → Response
```

Do **not** mechanically implement that mapping.

Reusable OpenAI Prompt objects are themselves being deprecated.

Current OpenAI guidance for new/long-lived integrations is to move reusable production prompt content back into application-managed code and pass the relevant configuration directly to Responses.

Therefore:

**Do not create new persistent OpenAI Prompt resources merely to imitate the old Assistant lifecycle.**

If Chatzilla already has configuration such as:

```text
YAML
Python configuration
bot archetypes
persona definitions
task instructions
model settings
tool/schema definitions
```

first determine whether those existing application-owned structures can remain the authoritative configuration.

A likely conceptual shape for current APIs is simply:

```text
application configuration
        ↓
model
instructions
input
tools/schema if needed
        ↓
Responses API
```

Again: inspect the repo before deciding exactly how this applies.

The goal is not to manufacture a replacement remote object just because an old remote Assistant used to exist.

---

# 4. AN IMPORTANT MENTAL-MODEL CHANGE

The Assistants API gave OpenAI more responsibility for orchestration.

A typical Assistants-style lifecycle could contain concepts such as:

```text
Assistant
   +
Thread
   +
Message
   +
Run
   ↓
poll/status
   ↓
requires_action
   ↓
submit_tool_outputs
   ↓
continue Run
   ↓
retrieve resulting message
```

The Responses API is more direct.

Conceptually:

```text
application sends input/configuration
        ↓
Response
        ↓
application inspects typed output items
        ↓
optional local action/tool execution
        ↓
application supplies resulting item(s)
        ↓
another Response if needed
```

This means some code that used to manage OpenAI resource lifecycle may no longer be necessary.

However:

**Do not delete that code merely because it looks obsolete.**

First migrate the relevant flow and prove that the replacement works.

Only then remove lifecycle machinery that is demonstrably unreachable or unnecessary, in the cleanup milestone already defined by the plan.

---

# 5. "ASSISTANT" MAY STILL BE A VALID APPLICATION CONCEPT

Do not confuse:

```text
an OpenAI Assistant API resource
```

with:

```text
an application concept representing a bot persona/task configuration
```

The former is gone.

The latter may still be completely useful.

For example, if the existing application has some local concept containing:

```text
name
instructions
model
behavior
task purpose
tool definitions
```

that object does not necessarily need to disappear.

Likewise, a class named something like:

```text
GPTAssistantManager
```

does not automatically need to be renamed.

Preserving an existing public interface or class name may be much less invasive than renaming it throughout the repository simply because OpenAI changed terminology.

Renaming is optional cleanup unless the existing name causes an actual implementation problem.

---

# 6. NORMAL TEXT GENERATION IS MUCH FLATTER NOW

For a basic request, the modern conceptual flow can be as small as:

```python
response = client.responses.create(
    model=...,
    instructions=...,
    input=...
)

text = response.output_text
```

This example is illustrative only.

Use whatever sync/async form matches the existing repository.

The important distinction is that basic text generation no longer inherently requires:

```text
create Assistant
create Thread
create Message
create Run
poll Run
retrieve Message
```

If an existing Chatzilla flow only needed those resources because that was how the Assistants API operated, the Responses implementation may collapse that workflow significantly.

Do not, however, flatten Chatzilla's own request/queue/task abstractions merely because the OpenAI call itself becomes flatter.

Keep the application's workflow.

Simplify the **OpenAI boundary**.

---

# 7. RESPONSE OUTPUT IS NOW ITEM-BASED

Do not assume that a Response is always just:

```text
one assistant message string
```

Responses use typed output items.

Depending on the request, output can include things such as:

```text
message/output text
function calls
tool-related items
reasoning-related items
other supported response items
```

For an ordinary text-only response, the Python SDK provides the convenient:

```python
response.output_text
```

property.

Use that where appropriate.

Do not write brittle parsing that assumes something such as:

```python
response.output[0].content[0]...
```

is universally the final text unless the exact response contract being implemented requires that structure.

Conversely, if processing tools or other typed output items, inspect `response.output` properly rather than relying only on `output_text`.

The correct behavior depends on the particular flow.

---

# 8. STATE IS NOW A CHOICE, NOT SOMETHING TO RECREATE AUTOMATICALLY

Do not assume old:

```text
Thread
```

must become new:

```text
Conversation
```

one-for-one.

Current Responses integrations can maintain continuity in several ways, including:

```text
fully independent/stateless requests

manual replay of relevant input/output items

previous_response_id

Conversations API
```

Determine what the old Chatzilla flow actually needed.

Questions to answer from the repository include:

```text
Was an old Thread reused?

Was it used only for one task?

Did it span multiple chat messages?

Did Chatzilla itself already assemble relevant history?

Was a Thread created because the Assistants API required one?

Is OpenAI-side persistence actually providing a feature the bot depends on?
```

Use the least stateful mechanism that preserves existing behavior.

Do not add persistent Conversations merely because they are available.

---

# 9. `previous_response_id` HAS SPECIFIC SEMANTICS

If a workflow genuinely benefits from chaining Responses, `previous_response_id` is one available mechanism.

Be aware of two important facts.

First:

```text
previous_response_id
```

can connect a later request to a prior Response.

Second:

**top-level `instructions` from the earlier Response are not automatically carried into the next request.**

If Chatzilla has stable persona/task instructions, those may need to continue being supplied by Chatzilla on subsequent requests.

This can actually fit an application-owned configuration model nicely because the bot remains responsible for defining its own behavior.

Do not assume chained Responses make prompt/instruction configuration persistent.

Also do not introduce response chaining where a completely independent request already contains everything necessary.

---

# 10. RESPONSE STORAGE IS DISTINCT FROM CONVERSATION DESIGN

Current Responses behavior can store Response objects server-side by default.

The API supports:

```python
store=False
```

for flows where server-side Response retention is not desired or required.

Current documentation states that ordinary stored Response objects have a default application-state retention period of approximately 30 days.

Conversation objects have different persistence semantics.

Do not choose `store=True`, `store=False`, or Conversations reflexively.

Determine what each flow needs.

Given this project's existing preference for simple application-owned state, it is reasonable to evaluate whether stateless calls with `store=False` fit particular tasks, but that is **not a blanket instruction to change every call to `store=False`**.

Document the decision where it matters.

---

# 11. OLD RUN STATUS / POLLING CODE MAY NO LONGER MAP DIRECTLY

Old Assistants code may contain logic involving:

```text
Run creation
Run retrieval
polling
queued
in_progress
completed
requires_action
failed
cancelled
expired
```

Do not blindly reproduce this entire status machine around Responses.

A normal foreground `responses.create(...)` call can simply return a Response.

Responses themselves have statuses, and background/streaming modes have their own lifecycle behavior, but that does not mean Chatzilla needs an elaborate polling system.

Determine whether the old polling existed because:

```text
the application genuinely needed asynchronous remote jobs
```

or merely because:

```text
Assistants Runs worked that way.
```

If it was purely API scaffolding, the new implementation may be much simpler.

Preserve only status handling required by the actual migrated behavior.

This project explicitly does **not** want generalized lifecycle/error orchestration added as part of the migration.

---

# 12. FUNCTION CALLING STILL EXISTS, BUT THE LOOP IS DIFFERENT

Real function/tool calling remains supported.

A modern Responses tool flow conceptually looks like:

```text
application sends Responses request + tool definitions
        ↓
response.output contains function_call
        ↓
application reads:
    function name
    arguments
    call_id
        ↓
application executes local function
        ↓
application supplies function_call_output
associated with the same call_id
        ↓
model continues and can produce final response
```

This differs from Assistants Runs where the application may previously have seen:

```text
Run.status == requires_action
```

and then submitted tool outputs back to the Run.

There is no need to reproduce `requires_action` as a fake internal state just to make new code resemble the old API.

Use the current Responses function-call contract.

---

# 13. `call_id` MATTERS

For actual function calling, a function request and the application's function result are associated through:

```text
call_id
```

Do not confuse this with unrelated IDs such as:

```text
response id
output item id
function name
old Run id
old tool-call object id semantics
```

The implementation needs to return the tool/function result against the appropriate call ID expected by Responses.

Where multiple function calls are possible, inspect all relevant output items rather than assuming exactly one unless the existing Chatzilla flow explicitly guarantees one.

At the same time:

**do not design a giant generic parallel tool runtime merely because the API supports multiple tool calls.**

Support the behavior Chatzilla actually uses.

---

# 14. DISTINGUISH REAL TOOLS FROM "TOOLS USED TO FORCE A RESULT"

This is one of the most important opportunities in this migration.

A genuine tool bridges the model to application functionality.

Example conceptually:

```text
model asks:
    look_up_something(x)

Python actually performs:
    look_up_something(x)

result goes back to model
```

That remains function calling.

However, older implementations often used function/tool schemas for something different:

```text
"I need the model to give me exactly YES/NO/MAYBE,
so I will define a function with an enum parameter
and read the selected argument."
```

That may not be a real tool at all.

It may simply have been a convenient way to force structured output.

For every old tool, inspect what happens after it is called.

Ask:

```text
Does Python actually perform an operation?

Does the model need the result of that operation?

Does anything external change?

Is application data retrieved?

Or is the tool-call argument itself the value Chatzilla wanted?
```

That distinction determines whether to use:

```text
Responses function calling
```

or:

```text
Responses Structured Outputs
```

Do not convert genuine functions into Structured Outputs.

Do not preserve fake tool loops if a direct structured result is clearly simpler.

---

# 15. STRUCTURED OUTPUTS ARE NOW A FIRST-CLASS OPTION

The Responses API supports Structured Outputs using JSON Schema.

For Responses, schema-controlled text output is configured through:

```text
text.format
```

rather than the older Chat Completions-style:

```text
response_format
```

pattern.

Structured Outputs can enforce schema adherence for supported models.

This is a good fit for existing Chatzilla tasks whose real desired result is something like:

```text
boolean

YES / NO

YES / NO / MAYBE

one value from an enum

small classification object

a couple of known fields
```

For example, conceptually:

```json
{
  "type": "object",
  "properties": {
    "classification": {
      "type": "string",
      "enum": ["YES", "NO", "MAYBE"]
    }
  },
  "required": ["classification"],
  "additionalProperties": false
}
```

could replace an older function call that existed solely to obtain one of those three values.

Do not introduce Pydantic everywhere simply because the Python SDK supports parsed schemas.

If the repository already uses plain dictionaries/JSON schemas and they remain easy to understand, keeping them may be preferable.

Use the smallest implementation consistent with the application's current coding style.

---

# 16. FUNCTION CALLING VS STRUCTURED OUTPUTS — SIMPLE RULE

Use this as a conceptual test:

```text
Does the model need Chatzilla/Python to DO something
or obtain something external?

YES
→ likely function calling

NO, Chatzilla just needs the model's answer in a known shape
→ likely Structured Output
```

This is a guideline, not an instruction to rewrite every existing tool.

Inspect each actual use case.

---

# 17. JSON MODE IS NOT THE SAME AS STRUCTURED OUTPUTS

If the repository contains older JSON-mode logic, do not assume:

```text
valid JSON
```

means:

```text
guaranteed schema
```

Current OpenAI documentation distinguishes basic JSON mode from Structured Outputs.

JSON mode focuses on producing syntactically valid JSON.

Structured Outputs constrain the model to a supplied schema.

If an old workflow contains significant parsing/retry/prompt machinery simply to enforce a tiny schema, consider whether Structured Outputs allow that code to become smaller.

Again, remove complexity only where migration directly makes it obsolete.

---

# 18. ASYNC SUPPORT EXISTS DIRECTLY IN THE CURRENT PYTHON SDK

The official Python SDK supports:

```python
from openai import AsyncOpenAI
```

and asynchronous calls such as:

```python
response = await client.responses.create(...)
```

The synchronous and asynchronous clients expose substantially corresponding functionality.

Chatzilla is known to have significant async behavior, but **do not use this fact as permission for an async refactor.**

Inspect how the existing OpenAI client is instantiated and invoked.

If an existing async path is blocking on a synchronous OpenAI request and switching that specific boundary to `AsyncOpenAI` is a small, direct migration improvement, that may make sense.

If doing so would cascade through unrelated code, preserve existing behavior unless correctness requires otherwise.

Do not reorganize queues/tasks/event handling as part of this API migration.

---

# 19. STREAMING IS OPTIONAL

Responses supports streaming.

That does **not** mean Chatzilla should adopt streaming as part of this migration.

Inspect whether the old application streamed model output.

If it did not:

```text
do not add streaming
```

just because the current API supports it.

If it did:

migrate the existing behavior narrowly, keeping in mind that Responses streaming emits typed events rather than necessarily matching whatever event/chunk shape older APIs used.

Streaming optimization can be revisited later if it is merely a nice-to-have.

---

# 20. BUILT-IN OPENAI TOOLS ARE NOT A MIGRATION REQUIREMENT

The Responses API supports many current OpenAI-hosted capabilities, including various built-in tools.

Do not introduce:

```text
web search
file search
computer use
shell
MCP
hosted code execution
agentic tooling
```

unless the existing Chatzilla behavior actually requires them and the migration plan calls for them.

The fact that Responses exposes more tools than the old API is irrelevant to this restoration effort.

Preserve Chatzilla's existing local functionality.

---

# 21. DO NOT INTRODUCE THE AGENTS SDK

The existence of OpenAI's agent tooling does not mean this project should be rewritten around it.

The existing plan explicitly calls for preserving the current application architecture.

Responses can be used directly.

Do not introduce:

```text
Agents SDK
new agent runtime
new orchestration framework
multi-agent architecture
handoff framework
new state framework
```

to replace Chatzilla's own simple request/task flow.

The migration should make the OpenAI integration **thinner**, not create a new framework around it.

---

# 22. MODEL SELECTION IS A SEPARATE DECISION FROM ENDPOINT MIGRATION

Do not conflate:

```text
Assistants API is dead
```

with:

```text
every old model must be replaced.
```

Those are separate questions.

For each active workload:

1. identify the model actually configured
2. verify whether it is currently supported on Responses
3. determine what the task actually requires
4. consider cost
5. change the model only where justified

As of this review, `gpt-4o-mini` remains a supported Responses model and is still positioned as a fast, inexpensive small model for focused tasks.

Therefore:

**do not replace `gpt-4o-mini` merely because it is not the newest model.**

This project is intentionally extremely cost-sensitive.

For simple classification/routing/enum-style tasks, favor inexpensive models that are sufficient.

For freeform chat/personality work, evaluate quality separately.

Do not default to the newest flagship model.

Do not default to reasoning models.

Do not spend more money merely for architectural neatness.

Model optimization can remain incremental after a working baseline exists.

---

# 23. WATCH FOR INVALID HISTORICAL FALLBACKS

The repository has already shown historical configuration/fallback strings.

Some may be:

```text
currently supported
historical comments
obsolete models
typos
unused fallback values
```

Do not treat every model string found by repository search as active.

Trace the configuration path.

Distinguish:

```text
active YAML value
default fallback
commented historical note
dead configuration
```

Only fix values that affect reachable code or create a realistic bad fallback.

Do not perform a cosmetic purge of every old model reference.

---

# 24. TTS IS A SEPARATE API SURFACE

Responses migration does not imply that audio speech generation needs to move into Responses.

OpenAI continues to expose text-to-speech through the Audio/Speech API.

Current documentation still lists:

```text
tts-1
tts-1-hd
```

and also recommends the newer:

```text
gpt-4o-mini-tts
```

for newer speech capabilities.

Therefore, when the migration reaches TTS:

1. inspect the existing service
2. identify its exact API call
3. verify whether its configured model remains supported
4. verify SDK compatibility
5. migrate only if required or clearly worthwhile

Do not automatically replace `tts-1`.

The old `tts-1` model remains documented and may have latency/cost/behavior characteristics the existing application intentionally preferred.

Treat a switch to a newer TTS model as a separate model decision unless the existing endpoint no longer works.

---

# 25. CHAT COMPLETIONS, IF FOUND, ARE NOT THE SAME PROBLEM AS ASSISTANTS

If repository inspection finds use of:

```python
client.chat.completions.create(...)
```

do not automatically classify it as broken merely because Assistants shut down.

Chat Completions remains supported.

The current OpenAI direction for new general generation work is Responses, and the migration plan may still choose to consolidate relevant functionality there, but existing working Chat Completions usage is not equivalent to the dead Assistants endpoint.

If found:

```text
document it
determine whether the plan requires changing it
avoid scope creep
```

A functioning unrelated Chat Completions path does not need to be rewritten merely for consistency unless there is a concrete benefit.

---

# 26. THE RESPONSE OBJECT CAN HAVE MORE THAN "SUCCESS TEXT"

Current Responses have lifecycle/status information such as completed/incomplete/failed and may expose additional states in specialized modes.

Do not ignore actual error responses.

But equally:

**do not recreate an elaborate Assistants Run status framework around them.**

For ordinary foreground Chatzilla calls, implement only the minimal success/failure handling necessary to restore behavior.

This project explicitly prefers straightforward failures that are understandable during manual development over extensive defensive abstraction.

---

# 27. PRESERVE APPLICATION-OWNED CONTEXT ROUTING

An API migration should not steal responsibility from Chatzilla's existing task/request/queue system.

If existing application objects already identify things such as:

```text
originating Twitch context
request type
user/context
instructions
desired task
result destination
```

continue to use those mechanisms.

Do not move that information into OpenAI metadata/state just because Responses exposes fields that could hold it.

Do not introduce OpenAI persistence as an application message bus.

OpenAI should perform the model operation.

Chatzilla should continue orchestrating Chatzilla.

---

# 28. KEEP PUBLIC CALLING SHAPES STABLE WHERE PRACTICAL

Suppose downstream application code currently does something conceptually like:

```python
result = manager.some_existing_method(request)
```

and the implementation underneath currently performs Assistants operations.

Prefer changing the internals while preserving the existing calling contract where reasonable.

Do not force unrelated callers to understand Responses API terminology if they do not need to.

A good migration boundary often looks like:

```text
existing Chatzilla interface
        ↓
changed OpenAI implementation underneath
```

rather than:

```text
change OpenAI API
        ↓
change every caller
        ↓
change every request object
        ↓
change queues
        ↓
change bot handlers
```

Only propagate interface changes when the new behavior actually requires them.

---

# 29. DO NOT PRESERVE OBSOLETE REMOTE IDS JUST FOR COMPATIBILITY

Old Assistants code may contain persisted or runtime values such as:

```text
assistant_id
thread_id
run_id
```

Some of these may no longer serve a purpose.

Do not create fake IDs or placeholder resources merely to preserve fields internally.

However, do not remove them immediately either.

Trace how each value is used.

Classify each as:

```text
still required
replaced by a Responses concept
application-only metadata
obsolete after migration
unknown until later milestone
```

Remove obsolete ID/lifecycle code only once the migrated flow has been proven and the cleanup milestone is reached.

---

# 30. RESPONSE IDS SHOULD NOT AUTOMATICALLY BECOME NEW APPLICATION STATE

Responses expose IDs.

That does not mean Chatzilla needs to start storing every response ID.

Store/pass one only when an actual workflow needs it, such as deliberate use of:

```text
previous_response_id
```

or another supported continuation mechanism.

Do not turn Response IDs into a new persistence architecture.

---

# 31. DO NOT OVER-ENGINEER TOOL LOOPS

For a real tool, the simplest understandable implementation is desirable.

Conceptually:

```text
send request
inspect output
find function call
parse arguments
execute known local function
construct function_call_output with correct call_id
send continuation
read result
```

If the existing application requires multiple iterations, support them.

If it requires only one simple operation, do not build an enterprise-grade generalized tool engine in anticipation of imaginary future use.

If the existing implementation already has a reasonably understandable loop that can be adapted, adapt it.

---

# 32. BE CAREFUL ABOUT PARALLEL TOOL CALLS

Current APIs may allow multiple tool calls.

Do not assume:

```text
there will always be exactly one
```

unless the specific workflow guarantees it.

But also do not implement complex concurrent tool orchestration merely because parallel calls are possible.

Look at the actual tools and task expectations in Chatzilla.

Implement what existing functionality requires.

Document anything outside that range as a later consideration rather than silently broadening scope.

---

# 33. STRICT TOOL SCHEMAS CAN HELP WITHOUT BECOMING A NEW FRAMEWORK

Current function definitions can use structured parameter schemas and strict behavior.

Use enough schema definition to prevent obvious invalid arguments.

Do not turn this into a schema-design project.

Existing simple tools should remain simple.

For example:

```text
one enum parameter
```

should not become:

```text
several new nested Pydantic classes
generic parser abstraction
validation service
tool registry framework
```

unless the current code already works that way.

---

# 34. KEEP INSTRUCTIONS IN APPLICATION CODE/CONFIGURATION

Current OpenAI guidance is moving prompt/instruction ownership into normal application code rather than persistent API-managed Prompt resources.

This aligns well with the migration philosophy already documented.

Where existing Chatzilla instructions live in:

```text
YAML
data files
bot archetypes
Python
configuration
```

preserve that ownership unless the repository proves otherwise.

Do not upload them into a new remote prompt-management lifecycle just to mirror old Assistants behavior.

---

# 35. DO NOT MIX MIGRATION WITH PROMPT REWRITING

If an old persona/task prompt still expresses the intended behavior, migrate it first.

Do not simultaneously:

```text
rewrite personality
"improve" system prompts
restructure all instructions
change tone
change task definitions
optimize prompt engineering
```

unless a new API requirement genuinely forces a syntax/structure change.

Behavioral differences become much harder to diagnose if both:

```text
API mechanics
```

and:

```text
prompt content
```

change at the same time.

Preserve prompt semantics first.

Optimize later.

---

# 36. CURRENT API FEATURES ARE NOT REQUIREMENTS

Responses supports capabilities that did not exist when this project was created.

Ignore them unless useful to the existing product.

The migration target is not:

> "What would we build if Chatzilla were started in 2026?"

The target is:

> "What is the smallest current implementation that restores the Chatzilla that already exists?"

That distinction should guide every decision.

---

# 37. COST SHOULD BE VISIBLE, NOT JUST MODEL NAME

When assessing model choice, remember that endpoint choice itself is not generally the major cost distinction.

Token usage and selected model matter.

Where useful, note:

```text
model
input-token price
output-token price
likely call frequency
likely output length
```

but do not build a cost-accounting subsystem.

This application may make many lightweight calls, so cheap classifications can matter more than theoretical maximum intelligence.

The first working baseline should favor low-cost adequate models.

Quality upgrades can happen after functionality is restored.

---

# 38. STATE CAN ALSO HAVE COST CONSEQUENCES

When using chained model context, previous context is not magically free.

Current documentation notes that when using `previous_response_id`, prior input represented in the chain continues to contribute to input-token billing.

Therefore do not create unnecessarily long chains for tiny independent tasks.

If a task is naturally independent:

```text
make it independent
```

rather than attaching it to a growing conversation simply because state continuation is available.

This is especially relevant in a bot that may perform many small classifications or helper operations.

---

# 39. KEEP SECONDARY MIGRATIONS SECONDARY

If inspection discovers:

```text
old TwitchIO
old unrelated package
old logging style
old local ML package
old config convention
unused dead file
style issue
type-hint issue
```

do not mix those changes into the OpenAI migration.

Meaningful discoveries can be placed into the appendix already defined by the plan.

The appendix should contain only real findings worth remembering.

Do not turn it into generic technical debt.

---

# 40. CURRENT OFFICIAL DOCUMENTATION SHOULD WIN OVER MEMORY

Before implementing specific SDK syntax, verify it against the current official OpenAI documentation and/or the installed/current official Python SDK.

Important topics worth checking when encountered include:

```text
Responses create syntax
AsyncOpenAI usage
text.format Structured Outputs
function tool definitions
function_call item shape
function_call_output item shape
call_id handling
previous_response_id
conversation parameter
store behavior
response.output/output_text
streaming events if actually used
Audio/Speech syntax
current model support
current model pricing
```

Do not rely on examples remembered from older Chat Completions or Assistants implementations.

OpenAI APIs changed substantially during the period this repository was dormant.

---

# 41. DO NOT FOLLOW OLD ONLINE EXAMPLES BLINDLY

There is now a large amount of obsolete OpenAI example code online.

Be particularly suspicious of examples centered on:

```text
beta.assistants
beta.threads
threads.runs
requires_action
submit_tool_outputs on a Run
persistent Assistant IDs
old prompt-object migration advice
old model aliases
```

Use current official docs first.

When Stack Overflow/blog/example code conflicts with current official documentation, follow official documentation.

---

# 42. USER-CONTROLLED API EXECUTION REMAINS A HARD RULE

Do not make live OpenAI API calls yourself unless I explicitly authorize a particular call.

This remains true during implementation milestones.

You may:

```text
edit code
inspect code
search repository
run static/local checks
import modules where doing so does not trigger OpenAI
run version inspection
compile/check syntax
prepare commands
```

But when the next validation step would actually invoke OpenAI:

**stop and give me the command/action.**

Examples include:

```text
python SomeClass.py

calling a class main() that invokes OpenAI

starting the bot if startup invokes OpenAI

running an OpenAI shell script

sending a Responses request

triggering function calling

triggering Structured Outputs

generating TTS
```

Tell me:

```text
1. exactly what to run
2. what successful behavior should look like
3. what output/error to paste back
```

I will perform the call.

Use my returned output to continue implementation/debugging.

Do not silently run "one quick API smoke test."

---

# 43. CLASS `main()` / DIRECT EXECUTION IS A FEATURE OF THIS DEVELOPMENT STYLE

Where the repository already has useful:

```python
if __name__ == "__main__":
```

blocks or equivalent example execution functions, preserve that development style.

I like being able to execute a class/module and manually observe one complete representative operation.

If a current example needs a small migration update to remain useful, that is preferable to building a separate test harness.

When appropriate, use these existing entry points as milestone validation.

Do not remove them because they look informal.

This is a personal development/debugging affordance that I intentionally value.

---

# 44. IMPLEMENT THE EXISTING PLAN IN MILESTONES, NOT ALL AT ONCE

The migration plan deliberately divides work into resumable milestones.

Respect those boundaries.

For each milestone:

```text
inspect
implement only that slice
perform non-API checks
update plan status
prepare user-run live validation
stop for results
fix if necessary
establish milestone exit criteria
commit-worthy stable point
move on
```

Do not implement Milestones 1–6 in one giant batch because you believe you understand the migration.

The objective is to establish one known-good pattern and expand from there.

This also makes it easier to return to the project weeks later.

---

# 45. KEEP THE PLAN ARTIFACT CURRENT AS IMPLEMENTATION PROGRESSES

The Markdown migration plan is a working artifact, not a one-time audit report.

As real implementation reveals facts:

```text
update milestone status
record decisions
correct earlier assumptions
record actual files changed
update NEXT ACTION
record blockers
mark unnecessary milestones NOT REQUIRED
move genuine deferred discoveries to appendix
```

Do not leave the document describing an obsolete understanding of the implementation.

At the end of a session, someone should be able to open the plan and understand where the migration actually stands without reconstructing it from Codex chat history.

---

# 46. WHEN REPOSITORY REALITY DIFFERS FROM THE PLAN

The plan was intentionally created before implementation.

Some assumptions may prove incorrect.

If inspection proves that a planned migration step is unnecessary:

```text
do not manufacture the work
```

Update the plan.

If a supposed tool is actually only an enum-output workaround:

```text
record that discovery
consider Structured Outputs
```

If an assumed persistent thread is actually thrown away immediately:

```text
record that discovery
do not add a Conversation merely for symmetry
```

If TTS still works untouched:

```text
record that
mark migration unnecessary
```

If there are no genuine tools left after structured-output migration:

```text
mark the genuine-tool milestone NOT REQUIRED
```

The plan is intended to guide reality, not override it.

---

# 47. EXPECT SOME DELETION TO BE A SUCCESSFUL MIGRATION OUTCOME

This migration may result in fewer lines of OpenAI integration code.

That is acceptable and potentially desirable.

Some old code may exist solely for:

```text
creating remote Assistants
maintaining Assistant IDs
creating temporary Threads
creating Runs
polling Runs
processing requires_action
submitting fake tool outputs
retrieving final Thread Messages
```

If current Responses functionality proves those layers unnecessary, they can eventually be removed.

But deletion should follow successful replacement and validation.

Do not perform speculative cleanup ahead of working functionality.

---

# 48. DO NOT CONFUSE SIMPLIFICATION WITH REFACTORING

This distinction matters.

Good migration simplification:

```text
old API required five lifecycle calls;
new API requires one Responses call;
remove now-unused lifecycle code after validation
```

Unwanted refactoring:

```text
while changing the endpoint,
replace managers,
rename every class,
introduce repository pattern,
move configuration,
rewrite queue system,
create framework
```

The first is directly caused by API evolution.

The second is scope creep.

Prefer the first.

Avoid the second.

---

# 49. GENERIC OLD → CURRENT CONCEPTUAL REFERENCE

This is only a conceptual reference.

Do not assume every row exists in Chatzilla.

| Older concept | Current concept to investigate |
|---|---|
| Assistant remote resource | Usually application-managed instructions/config + Responses |
| Assistant instructions | `instructions` / application-managed prompt content |
| Thread | Stateless input, manual item history, `previous_response_id`, or Conversation depending on actual need |
| Thread Message | Responses input/output items |
| Run | Response |
| Poll Run | Often unnecessary for ordinary foreground Responses calls |
| `requires_action` | Inspect `function_call` output item(s) |
| Tool call arguments | Function-call item arguments |
| `submit_tool_outputs` | Supply `function_call_output` with matching `call_id` |
| Final Thread Message retrieval | Response output / `output_text` when appropriate |
| Tool used only to force enum | Candidate for Structured Outputs |
| `response_format` structured schema | Responses `text.format` |
| Persistent OpenAI Prompt | Avoid for new long-lived design; keep prompts/instructions in application code |
| Assistant ID | Often unnecessary; verify caller dependencies |
| Thread ID | Only replace with state mechanism if state is actually required |

Treat this table as a checklist for investigation, not a required mapping.

---

# 50. THREE COMMON MIGRATION SHAPES TO RECOGNIZE

These are generic examples, not claims about Chatzilla.

## Pattern A — ordinary text

Old conceptual flow:

```text
select Assistant
create/reuse Thread
add Message
create Run
wait
retrieve final Message
```

Possible current flow:

```text
load existing local configuration
responses.create(model, instructions, input)
read output_text
return through existing application workflow
```

---

## Pattern B — classification disguised as a tool

Old conceptual flow:

```text
ask Assistant
Run requires action
model "calls" classification tool
read enum argument
possibly submit output
continue
```

Possible current flow:

```text
responses.create(
    input,
    structured text schema
)

parse schema-conforming classification
return enum through existing application workflow
```

---

## Pattern C — real application function

Old conceptual flow:

```text
Assistant Run
↓
requires_action
↓
Python function
↓
submit_tool_outputs
↓
continue Run
↓
retrieve final message
```

Possible current flow:

```text
Responses request + function definition
↓
function_call output item
↓
Python executes existing function
↓
function_call_output using call_id
↓
next Response
↓
final result
```

Use whichever pattern the actual code requires.

Do not force every call into one universal abstraction.

---

# 51. WHAT A GOOD END STATE SHOULD FEEL LIKE

Do not optimize for novelty.

A successful migration should leave the repository feeling like:

> "This is still the application I built. The OpenAI calls underneath it now use the current API and some old API scaffolding disappeared."

It should **not** feel like:

> "An AI coding agent replaced my personal project with a 2026 agent platform."

The application should remain recognizable.

The request/task flow should remain recognizable.

Configuration should remain recognizable.

Tools should remain recognizable where they are real tools.

Simple classification may become simpler.

Remote Assistant/Run lifecycle code may disappear.

Everything else should change only where there is a concrete reason.

---

# 52. IMPLEMENTATION PRIORITY

When choosing between two valid migrations, prefer in this order:

```text
1. preserves existing behavior
2. preserves existing application interfaces
3. uses currently supported OpenAI APIs
4. is easy for the author to read
5. minimizes remote state
6. minimizes API calls
7. minimizes cost
8. removes directly obsolete API scaffolding
9. minimizes new abstractions
10. minimizes unrelated changes
```

Do not trade several of these away merely for a "cleaner" theoretical architecture.

---

# 53. FINAL OPERATING INSTRUCTION

Use these notes while implementing the existing migration plan.

Do not create a new migration strategy from them.

At each step:

```text
inspect actual repo
        ↓
identify actual old behavior
        ↓
identify current OpenAI equivalent
        ↓
choose smallest compatible change
        ↓
preserve surrounding Chatzilla workflow
        ↓
perform local/non-API verification
        ↓
give me exact live validation command
        ↓
I run API operation
        ↓
use returned result
        ↓
update PLAN.md
```

When uncertain about:

```text
repo architecture → inspect code

OpenAI API behavior → check current official docs

product intent → follow PLAN.md

whether to refactor → don't, unless required

whether to call the live API → don't; give me the command
```

The goal remains simple:

> **Implement the plan and restore Chatzilla using current OpenAI APIs without redesigning Chatzilla.**