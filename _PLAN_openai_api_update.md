# Chatzilla OpenAI API Migration — Repository Audit and Implementation Plan

You are working in my local `chatzilla_ai` repository.

This is an older personal project that I originally wrote myself. It has been mostly dormant for roughly 1.25 years and was initially built roughly 2.25 years ago.

The immediate problem is that its OpenAI integration was built around the Assistants API. That API has now been sunset, and the application currently fails during startup when it reaches code similar to:

```python
self.gpt_client.beta.assistants.create(...)
```

with an OpenAI 404.

Your job in this pass is **not to implement the migration**.

Your job is to perform a thorough repository-level audit of the OpenAI integration, understand how the existing application actually works, investigate the current supported OpenAI APIs/models against official current documentation, and produce a durable, milestone-based migration plan inside the repository.

## Primary objective

Restore this application with the **smallest practical set of changes**.

This is not a modernization project.

This is not a rewrite.

This is not an opportunity to impose contemporary production engineering patterns on a small personal application.

The existing architecture represents how the author understood and built the application. Preserve that architecture wherever possible.

The desired outcome is:

> Get the existing machine running again using current OpenAI APIs while keeping the implementation recognizable, readable, inexpensive, minimally stateful, and close to the author's original design.

---

# 1. NON-NEGOTIABLE ENGINEERING PHILOSOPHY

Treat these as hard constraints.

## Preserve before improving

Prefer:

```text
old working concept
    ↓
small API compatibility change
    ↓
working current equivalent
```

Do not default to:

```text
old working concept
    ↓
new abstraction
    ↓
new framework
    ↓
new state-management layer
    ↓
new architecture
```

If the existing code can reasonably be adapted in place, adapt it in place.

## Be extremely conservative about refactoring

Do NOT refactor simply because:

- a class could be renamed
- responsibilities could be reorganized
- newer Python idioms exist
- code could be more "enterprise"
- a framework could reduce boilerplate
- a state machine could formalize behavior
- dependency injection would be cleaner
- everything could become Pydantic models
- managers could be consolidated
- functions could be split into additional services
- error handling could be centralized
- retries could be generalized
- an orchestration framework could be introduced
- an Agent SDK exists
- LangChain or another agent framework exists

Do not introduce these things unless the migration is genuinely infeasible without them.

Assume the author values being able to open a file six months from now and understand the code more than maximizing abstraction purity.

## Keep error handling minimal

This is a localhost personal project.

Do not design production-grade resilience.

Do not introduce:

- generalized retry frameworks
- elaborate exception hierarchies
- circuit breakers
- state-recovery systems
- persistence systems
- extensive fallback chains
- elaborate validation frameworks
- defensive checks around every possible state
- logging infrastructure projects

Some existing error handling may itself be unnecessarily complicated. It is acceptable for the eventual plan to recommend **removing or simplifying** obsolete error-handling code if the new API flow makes it unnecessary.

Only retain/add safeguards that solve an immediate, realistic failure mode.

## Avoid new state

Bias toward the least stateful implementation that reproduces existing behavior.

Do not automatically introduce Conversations, databases, persistent response tracking, or conversation lifecycle management simply because OpenAI offers them.

Determine whether the application actually requires those things.

If a request already contains everything required to perform a task, prefer an independent request.

---

# 2. APPLICATION CONTEXT

Approximate repository structure:

```text
.github/
.vscode/
assets/
    ears/
    media/
    tts/
classes/
config/
    bot_user_configs/
    keys/
data/
    botears/
    bot_archetypes/
    randomfact/
    rules/
log/
models/
my_modules/
readme/
    diagrams/
services/
```

Important known areas include:

```text
classes/GPTAssistantManagerClass.py
classes/ConfigManagerClass.py
services/GPTTextToSpeechService.py
services/FaissService.py
config/bot_user_configs/
config/.env
requirements.txt
```

Do not assume these are the only relevant files.

Find the actual architecture.

---

# 3. CURRENT APPLICATION STYLE

The application is heavily asynchronous.

It uses TwitchIO and has an existing queue/task/request architecture that associates OpenAI work with the Twitch event/context that caused it.

There are existing request/task classes that carry contextual information around the application.

Conceptually these may include things like:

```text
task/request type
user message
Twitch/user information
context
instructions
metadata
desired result
```

These application-level request objects are important.

They are **my application workflow**, not something that should be replaced merely because the OpenAI API changed.

Preserve that architecture unless there is a specific incompatibility.

Do not replace my queue/request flow with OpenAI-side state management.

---

# 4. ASSISTANT USAGE

The old application has a GPT Assistant manager.

Inspect it carefully rather than assuming how it behaves.

Historically there were multiple Assistant configurations. The relationship was generally closer to:

```text
task → configured assistant/behavior → output
```

rather than a requirement for a giant persistent AI conversation.

There may be one-to-many mappings between tasks and Assistant configurations.

Determine:

- how Assistants were constructed
- when they were created
- whether they were recreated at startup
- which instructions each used
- how models were selected
- how tools were attached
- what state was actually stored remotely
- whether Threads were persistent or ephemeral
- whether IDs were cached
- whether any lifecycle management is now obsolete
- whether there is meaningful context that only existed inside OpenAI objects

Do not assume that replacing Assistant → Conversation is appropriate.

The old `GPTAssistantManagerClass` may remain named that way during the migration if preserving the name avoids unnecessary downstream changes.

A rename can be noted later as an optional cleanup.

Do not rename it just because it no longer manages an API resource literally named "Assistant."

---

# 5. CURRENT FAILURE

The current known startup failure occurs around:

```python
self.gpt_client.beta.assistants.create(...)
```

and produces:

```text
openai.NotFoundError: Error code: 404
```

The Assistants API has been sunset.

Use the current official OpenAI documentation as the authoritative source for the supported replacement.

Do not rely on remembered API behavior.

For migration research:

- prefer official OpenAI developer documentation
- verify endpoint/API status as of today
- verify Python SDK syntax as of today
- verify current model availability
- verify current model pricing where relevant
- verify Structured Outputs syntax
- verify function calling syntax
- verify text-to-speech status
- verify state/conversation options

Document important source URLs in the migration plan.

Do not use random blogs as the primary authority when official docs cover the subject.

---

# 6. OPENAI API INVENTORY

Search the **entire repository** for OpenAI usage.

Do not only inspect the line currently throwing the 404.

At minimum search for concepts/patterns around:

```text
openai
OpenAI
AsyncOpenAI

beta.assistants
assistants
assistant_id

beta.threads
threads
thread_id

runs
run_id
requires_action
submit_tool_outputs

tools
tool_choice
function
function_call

response_format
json_schema
structured output

chat.completions
completions

responses

audio
speech
tts

embeddings

moderation

files
vector stores

stream
streaming
```

Use repository search tools such as `rg` where available.

Build a complete inventory of files/functions/classes that depend directly or indirectly on OpenAI behavior.

Distinguish:

1. active OpenAI integrations
2. obsolete but reachable integration code
3. dead/unused code if confidently identifiable
4. commented historical configuration
5. unrelated AI/ML functionality

For example:

```text
services/FaissService.py
```

currently appears to use a local `SentenceTransformer` model such as:

```text
all-MiniLM-L6-v2
```

Do not mistakenly classify that as an OpenAI embedding integration unless actual repository inspection shows otherwise.

---

# 7. SDK / ENVIRONMENT BASELINE

The project primarily uses:

```text
requirements.txt
```

There may be old Conda residue.

We are **not migrating environment-management systems in this project**.

Inspect and record the existing environment situation, but do not propose moving Conda → venv/uv/Poetry/etc. as part of the migration.

Determine at minimum:

```text
Python version
OpenAI Python SDK version
TwitchIO version
relevant parsing/schema dependencies
requirements.txt constraints
actual imported OpenAI package path if helpful
```

Useful commands may include:

```powershell
python --version
python -c "import openai; print(openai.__version__, openai.__file__)"
pip show openai
pip show twitchio
pip list
```

Inspect `requirements.txt`.

Do not perform broad package upgrades.

Only dependency updates required for the OpenAI migration belong in the implementation plan.

Other stale dependencies belong, at most, in an appendix.

---

# 8. CONFIGURATION INVENTORY

Known configuration paths include:

```text
config/bot_user_configs/
config/.env
```

Known model configuration currently includes examples like:

```yaml
assistant_model: "gpt-4o"
assistant_model_light: "gpt-4o-mini"
tts_model: "tts-1"
```

Historical commented values include older GPT-4 and GPT-3.5 variants.

`ConfigManagerClass.py` currently has fallback/default strings including approximately:

```python
assistant_model -> gpt-3.5-turbo
assistant_model_light -> gpt-3.05-turbo
```

Note the probable typo in `gpt-3.05-turbo`.

Determine which values are active, which are fallback defaults, and which are merely commented historical notes.

Do not treat every model name found in comments as a live dependency.

Inventory:

- model configuration
- assistant identifiers
- thread identifiers
- API settings
- OpenAI-related environment variables
- TTS settings
- limits
- tool configuration
- any persistence/cache of remote resource IDs

### Secrets rule

Do not echo or copy secret values into the migration plan or console output.

Do not unnecessarily dump:

```text
config/keys/
config/.env
```

Inspect only what is needed to understand configuration names and behavior.

Never put credentials/tokens/API keys into the migration artifact.

---

# 9. MODEL-SELECTION REVIEW

Model selection is part of this migration.

However, **cost minimization is a major project requirement**.

This project is not currently trying to maximize model intelligence.

The current goal is:

> get a somewhat crude but working machine running inexpensively, then decide later where spending more money actually improves the experience.

Do not default to a flagship model.

Do not recommend expensive reasoning models simply because they are newer.

For every meaningful OpenAI workload, classify what it actually does.

Examples:

```text
freeform Twitch chat generation
simple classification
yes/no decision
enum selection
routing
small structured extraction
tool selection
longer creative output
TTS
```

Then identify the **lowest-cost currently supported model that is reasonably adequate** for that workload.

Model recommendations must be based on current official OpenAI availability/pricing at the time of analysis.

Do not assume that the old model names should simply be mechanically replaced.

Also do not recommend changing a working inexpensive model without a reason.

Create a small workload/model matrix in the migration plan containing:

```text
workload
current model/config
current purpose
migration concern
proposed current model
why
relative cost concern
whether change is required or optional
```

Separate:

```text
REQUIRED FOR COMPATIBILITY
```

from:

```text
OPTIONAL MODEL OPTIMIZATION
```

If the existing `gpt-4o-mini` remains supported and suitable for a workload, retaining it may be completely reasonable.

---

# 10. TOOL / FUNCTION CALLING REVIEW

This deserves especially careful inspection.

The old Assistants implementation used tools and a `requires_action` flow.

The application apparently detected tool requests and submitted tool outputs.

However, many of the "tools" were conceptually simple.

Some existed primarily to get a bounded result such as:

```text
TRUE / FALSE
YES / NO
YES / NO / MAYBE
an enum value
a simple classification
a small structured object
```

The result was then consumed elsewhere by my own application.

For **every existing tool**, determine whether it is actually:

### A. A genuine application action

Example concept:

```text
model requests an operation
Python function executes
function returns a result
model continues
```

or:

### B. A schema-enforcement workaround

Example:

```text
I want the model to choose exactly one enum
so I represented the enum selection as a tool
```

These two cases should not automatically be migrated the same way.

## For real tools

Preserve the local Python implementation.

Map the old Assistants tool execution flow onto the current Responses function-calling mechanism.

Keep the implementation straightforward.

Do not add an agent framework.

Do not make a generalized tool orchestration subsystem unless one already exists and remains useful.

## For enum/schema-only pseudo-tools

Investigate whether current Structured Outputs can replace the old tool round-trip more simply.

If:

```text
old tool loop
```

can safely become something conceptually like:

```text
one Responses request
+
small schema
+
parsed enum
```

then that may be a desirable migration simplification.

But only recommend it where it:

- preserves semantics
- clearly reduces code
- is locally understandable
- removes obsolete Assistants machinery
- does not require redesigning surrounding request classes

Do not broadly refactor all tool code merely because Structured Outputs exist.

Create a per-tool classification in the migration plan:

```text
tool/function name
caller
what it actually accomplishes
real side-effect/action? yes/no
current output shape
keep as function call?
candidate for Structured Output?
recommended migration
affected files
```

This section is important.

---

# 11. STRUCTURED OUTPUT REVIEW

Search for use of:

```text
response_format
JSON mode
JSON schemas
Pydantic parsing
manual JSON parsing
tool schemas used only for bounded output
```

Determine how the current application obtains predictable responses.

Compare this against current Responses API Structured Outputs.

Do not add schemas everywhere.

Use schemas only where the application already expects structured/bounded data or where replacing a fake tool call clearly simplifies the migration.

Keep simple text as simple text.

---

# 12. CONVERSATION / STATE REVIEW

Do not assume the app needs the Conversations API.

Determine what old Threads actually accomplished.

For every old thread-related flow, answer:

- Was the Thread reused?
- For how long?
- Across which users/tasks?
- Was history important?
- Did my application already include necessary history in the request?
- Was a Thread created only because Assistants required one?
- Was the Thread essentially temporary scaffolding?
- Does the current request object already provide sufficient context?

Evaluate the minimum current replacement among concepts such as:

```text
fully independent Responses request
manual supplied input/history
previous_response_id
Conversation object
```

Bias toward the least stateful option that preserves behavior.

If old Threads were effectively disposable task containers, do **not** introduce persistent Conversations simply to preserve a one-to-one conceptual mapping.

---

# 13. ASYNC / QUEUE BEHAVIOR

The application is async-heavy.

Its existing queue/request flow associates model work with particular Twitch events and contexts.

Preserve that.

Inspect:

```text
async def usage
OpenAI vs AsyncOpenAI clients
await boundaries
queue consumers/producers
where OpenAI calls actually execute
how results return to the originating task/context
```

Determine whether current OpenAI calls block inside async functions.

However:

**do not turn this into an application-wide async cleanup.**

If switching a specific OpenAI boundary to the current SDK's async client is a small and obvious compatibility improvement, include it in the plan.

If fixing it would cascade through the application, defer it unless required for correct operation.

Do not replace the queue architecture.

## Suppressed automatic output and conversation history

The current automatic-conversation flow can finish generating an assistant response and then suppress Twitch delivery because a requested reply took priority or another bot reply made the automatic work stale. With Assistants/Threads, that generated assistant message can remain in the remote thread even though chat never saw it. A later request may then treat unseen output as shared conversation history.

The migration must make this behavior explicit. Prevent unnecessary automatic generation before the API call where the existing gates allow it. Where a late delivery check is still required, suppressed model output must not become visible conversation context for later requests. Preserve the existing requested-reply priority and stale-reply checks without adding a persistent response registry solely for this case.

Live verification must cover this sequence: start automatic generation, queue or deliver a requested reply before the automatic response is sent, confirm that only the requested reply reaches Twitch, then confirm the next response does not assume chat saw the suppressed automatic output.

---

# 14. STREAMING

Do not assume OpenAI responses are streamed.

Inspect actual code.

If responses are currently non-streaming, keep non-streaming behavior unless migration forces otherwise.

If they are streamed, identify exactly how streaming events feed the current queue/Twitch behavior and plan the minimum event-handling update required by Responses.

Streaming enhancements belong in the appendix unless existing behavior requires them.

---

# 15. TEXT TO SPEECH

There is known TTS code around:

```text
services/GPTTextToSpeechService.py
```

and config approximately:

```yaml
tts_model: "tts-1"
```

Inspect it.

Determine:

- whether the endpoint still works
- whether SDK syntax has changed
- whether the configured model is still supported
- whether migration is actually required
- whether a newer model would materially alter cost/quality/latency

Do not replace TTS simply because a newer model exists.

If the existing endpoint/model remains supported, explicitly say that no migration is necessary.

If a newer model is merely interesting, put it in an appendix.

The immediate target is restoration.

---

# 16. TWITCH IS OUT OF SCOPE

Twitch currently authenticates and gets far enough to reach the failing OpenAI initialization.

Do not perform a TwitchIO migration/review in this pass.

Do not expand the project into a Twitch modernization effort.

Treat Twitch behavior as an existing boundary unless an OpenAI migration issue directly crosses it.

Unrelated Twitch concerns can appear only in a short appendix if something important is discovered accidentally.

---

# 17. TESTING PHILOSOPHY

Do not build a new test suite.

If relevant tests already exist:

- inspect them
- identify obvious updates required by the migration
- reuse them where convenient

Do not create a testing architecture.

For this personal project, manual executable validation is preferred.

Many classes may contain a `main()` or similarly runnable example representing one fairly complete normal use case.

I intentionally like this pattern because I can run the code, watch what happens, and understand the system manually.

Preserve and use that style where appropriate.

The migration plan should include **human-runnable validation commands/use cases** for milestones.

I am happy to run these interactively.

Prefer validation like:

```text
run class/module main()
observe one API request
inspect returned structured result
boot bot
send hello
observe bot response
trigger one representative classification
trigger one real tool flow
trigger TTS
```

over building dozens of unit tests.

---

# 18. FIRST-PASS GIT SAFETY

Before touching files:

```text
inspect git status
inspect current branch
note uncommitted files
```

Never discard, reset, checkout over, clean, or rewrite user work.

Do not perform a broad formatter pass.

Do not make unrelated whitespace changes.

During this first audit, the only repository file you should normally create or modify is the migration-plan Markdown described below.

---

# 19. REQUIRED FIRST-PASS OUTPUT ARTIFACT

Create a durable root-level Markdown file:

```text
OPENAI_MIGRATION_PLAN.md
```

If an obviously equivalent migration-plan file already exists, inspect it and update that instead rather than creating a duplicate.

Do **not** merely print the plan into Codex chat.

The repository artifact is the source of truth.

The purpose of this file is that I should be able to return to the project three weeks later, give a coding agent this file, and immediately know:

```text
what we learned
what decisions were made
what is finished
what is next
where to start
how to validate it
what we deliberately deferred
```

---

# 20. REQUIRED PLAN STRUCTURE

Use approximately the following structure.

Adapt it where repository findings justify doing so.

## Header / Resume Block

At the very top include something concise like:

```markdown
# OpenAI Migration Plan

Last reviewed:
Current migration status:
Current milestone:
Last completed milestone:
NEXT ACTION:
Primary blocker:
```

`NEXT ACTION` should be exceptionally concrete.

For example:

```text
Update GPTAssistantManagerClass._create_assistant() replacement path
to make one direct Responses request using the existing assistant
instruction configuration.
```

Not:

```text
Continue migration.
```

This block exists specifically so someone can resume the project quickly.

---

## 1. Migration Goal

Briefly state:

- Assistants API is dead
- restore working OpenAI behavior
- Responses is the likely target
- preserve application architecture
- minimize cost
- minimize refactoring/state
- localhost personal-project constraints

---

## 2. Hard Constraints

Record the constraints from this prompt so later agents do not slowly turn the migration into a rewrite.

Examples:

```text
No architecture rewrite.
No agent framework.
No broad dependency modernization.
No new persistence unless proven necessary.
No generalized retry/error system.
No new test framework.
Preserve task/request/queue design.
Prefer minimal API substitution.
Cost-sensitive model selection.
Manual main()-style verification is acceptable/preferred.
```

---

## 3. Current Architecture

Explain the OpenAI-related flow you discover.

Use actual classes/functions.

For example, determine something resembling:

```text
Twitch event
  ↓
request/task object
  ↓
queue
  ↓
GPT manager
  ↓
assistant selection/configuration
  ↓
OpenAI call
  ↓
tool/structured result if applicable
  ↓
task result
  ↓
original Twitch context
```

Do not invent this architecture.

Document what actually exists.

A simple Mermaid diagram is welcome if it genuinely makes this easier to understand, but do not spend significant time beautifying diagrams.

---

## 4. Current OpenAI Surface Area

Create a table such as:

```text
File
Class/function
Old endpoint/concept
Purpose
Currently reachable?
Migration required?
Notes
```

Include all meaningful OpenAI usage.

---

## 5. Old → Current Concept Mapping

Map actual repository concepts, not merely documentation terminology.

Potential entries may include:

```text
Assistant
Assistant instructions
Assistant tools
Thread
Message
Run
requires_action
submit_tool_outputs
response_format
audio.speech
```

For each, state:

```text
old usage in this repo
current API equivalent
whether exact replacement is necessary
recommended minimal adaptation
```

Do not assume every old object needs a corresponding new remote object.

---

## 6. State / Thread Decision

Explicitly document whether this application needs:

```text
stateless Responses
previous_response_id
Conversations
manual history
some mix by workflow
```

Include the evidence from the code that led to the decision.

The preferred answer is the least stateful one that works, not the fanciest one.

---

## 7. Tool / Structured Output Audit

Include the per-tool table described earlier.

This should make it obvious which existing tool machinery can potentially disappear because it was only being used for bounded classification.

---

## 8. Model and Cost Audit

Include the workload/model matrix.

Use current official OpenAI information.

Favor low-cost models.

Mark expensive/higher-intelligence alternatives as optional rather than defaults unless clearly necessary.

---

## 9. Dependency Changes

List only changes actually relevant to this migration.

Example format:

```text
Package
Current version/constraint
Proposed version/constraint
Why required
Risk
```

Do not list unrelated package upgrades here.

---

## 10. File-by-File Impact Map

Before implementation begins, identify likely edits.

Example:

```text
classes/GPTAssistantManagerClass.py
- replace dead Assistants resource creation
- revise run/tool loop
- preserve public interface where practical

classes/ConfigManagerClass.py
- update only invalid model defaults/config semantics

config/bot_user_configs/chatzilla_ai.yaml
- update active model configuration if required

requirements.txt
- update OpenAI SDK only as necessary
```

Use the actual repository findings.

Label each change:

```text
REQUIRED
LIKELY
OPTIONAL
```

---

# 21. MIGRATION MILESTONES

The implementation must be divisible into meaningful milestones.

Each milestone needs:

```text
Status
Goal
Scope
Likely files
Implementation outline
Manual validation
Exit criteria
Known follow-up
```

Use simple statuses:

```text
NOT STARTED
IN PROGRESS
BLOCKED
DONE
```

Avoid elaborate project-management machinery.

## Suggested shape

Do not blindly use these exact boundaries if the code suggests better ones, but aim for roughly this progression.

### Milestone 0 — Audit and migration decisions

Goal:

```text
Fully understand OpenAI usage and agree on replacement approach.
```

Exit criteria:

```text
OPENAI_MIGRATION_PLAN.md exists
OpenAI surface area identified
state strategy chosen
tool strategy chosen
initial model strategy chosen
file impact map documented
```

This first Codex session should complete **Milestone 0 only**.

---

### Milestone 1 — First living OpenAI path

Target the smallest meaningful vertical slice.

Desired outcome conceptually:

```text
launch application
Twitch authenticates
existing assistant-role/configuration objects initialize
no call is made to the dead Assistants endpoint
send/trigger first simple "hello chat" style request
receive a valid OpenAI response
return it through the existing application flow
```

Important:

The old application may have literally "created assistants" during boot.

The new API may not require remote Assistant creation at all.

Preserve the **application concept** of initialized assistant/persona/task configurations without artificially recreating remote resources that no longer need to exist.

This milestone should establish the migration pattern without converting every advanced workflow.

---

### Milestone 2 — Normal text/task flows

Migrate remaining ordinary text generation/task→output paths using the pattern proven in Milestone 1.

Preserve:

```text
request classes
queue behavior
context routing
existing instructions
existing calling interfaces where practical
```

Exit criteria should include several representative normal requests.

---

### Milestone 3 — Structured classifications / pseudo-tools

Migrate simple bounded-result tasks.

For each:

```text
keep function tool
OR
replace with Structured Output
```

based on the audit.

This milestone is a good place to simplify old `requires_action` machinery **only where doing so directly reduces now-obsolete code**.

Validate examples such as:

```text
boolean
yes/no/maybe
enum
small classification
```

---

### Milestone 4 — Genuine function/tool flows

If genuine function calls remain:

- migrate them to current Responses function calling
- preserve local Python functions
- use the simplest explicit tool loop that works
- correctly associate calls/outputs
- do not build a generalized agent runtime

If the audit discovers there are no genuine tools after Milestone 3, explicitly mark this milestone:

```text
NOT REQUIRED
```

rather than inventing work.

---

### Milestone 5 — TTS / secondary OpenAI endpoints

Verify TTS and any other OpenAI endpoint discovered by the audit.

Only migrate what is actually broken/outdated.

Do not replace working services merely to use newer APIs.

---

### Milestone 6 — Remove dead migration scaffolding

After all required paths work:

- remove unreachable Assistants-specific calls
- remove obsolete remote-ID lifecycle code if no longer needed
- simplify code made redundant by the migration
- update active config comments where genuinely misleading

Keep cleanup narrow.

Do not turn this milestone into generic refactoring.

---

### Milestone 7 — Working baseline / handoff

Final restoration baseline:

```text
bot boots
Twitch integration still works
primary chat response works
structured tasks work
required tools work
TTS works if currently part of normal use
no Assistants endpoint remains on a reachable path
model configuration is supported/current
cost posture is documented
```

Update the Resume Block so future work starts from a clear stable point.

---

# 22. APPENDIX — MEANINGFUL DEFERRED ITEMS ONLY

Create an appendix for findings that are useful but intentionally out of scope.

Possible examples:

```text
TwitchIO version is old and should eventually be reviewed
a class name now reflects the old Assistants terminology
potential async cleanup
newer TTS model worth evaluating later
streaming could improve responsiveness
larger model could improve a particular workload
dependency X is deprecated
existing code has an obvious unrelated bug
a test would be useful if this code becomes important
```

However:

**Do not create a giant generic technical-debt list.**

Do not fill the appendix with:

```text
add more unit tests
add more logging
improve documentation
add retries
use dependency injection
improve type hints
add CI
improve observability
```

unless you discovered a specific concrete reason relevant to this application.

This project is not being prepared for production or shipment.

Deferred items should be interesting enough that the author may realistically choose to revisit them.

---

# 23. DECISION LOG

Include a small decision log in the Markdown.

For significant migration choices record:

```text
Decision
Reason
Alternative rejected
Revisit when
```

Examples:

```text
Use stateless Responses for classification tasks.
Reason: request object already contains all context.
Rejected: persistent Conversations.
Revisit: only if future chat-history requirements appear.
```

or:

```text
Replace tool X with Structured Output.
Reason: tool had no side effect and existed only to obtain an enum.
Rejected: reproducing old function-call loop.
```

This is important because I may return weeks later and otherwise forget why something was chosen.

Keep the log small and meaningful.

---

# 24. THINGS TO ACTIVELY QUESTION

During the audit, explicitly challenge these assumptions:

### "Assistant" must become another persistent AI object

Maybe not.

Determine what Assistant creation was actually buying us.

### Thread must become Conversation

Maybe not.

If it was temporary scaffolding, eliminate unnecessary state.

### Every old tool must remain a tool

Maybe not.

Some may now be simpler Structured Outputs.

### Every configured old model must change

Maybe not.

Check actual support/cost.

### TTS must migrate

Maybe not.

Check whether it still works.

### Sync OpenAI client inside async application must become an async rewrite

Maybe only one boundary needs adjustment.

### Old code that handled Assistant lifecycle must remain

Maybe remote resource lifecycle code can disappear entirely.

### New API capability should be adopted because it exists

No.

Only adopt capability that directly improves compatibility, simplicity, or cost.

---

# 25. THINGS YOU MUST NOT INTRODUCE WITHOUT STRONG EVIDENCE

Do not introduce any of these merely as preferences:

```text
OpenAI Agents SDK
LangChain
LlamaIndex
new database
Redis
new task queue
new state machine
new persistence layer
conversation-memory service
generic tool framework
generic retry service
generic error framework
new DI container
new configuration library
new logging stack
new test framework
Dockerization
cloud deployment
environment-manager migration
```

This list is intentionally strict.

---

# 26. WORKING WITH EXISTING `main()` FLOWS

Look for executable:

```python
if __name__ == "__main__":
```

blocks, `main()` methods/functions, demo functions, or other direct execution examples.

Document which ones provide useful end-to-end verification.

When planning milestones, prefer these as validation surfaces.

If one existing `main()` can be minimally adjusted later to demonstrate the new API call from beginning to end, that is desirable.

Do not build a separate demo harness unless no useful runnable path exists.

---

# 27. FIRST-PASS EXECUTION RULES

For this session:

## You MAY

- inspect files
- search code
- inspect current package versions
- read current official OpenAI docs
- run non-destructive repository/environment inspection
- inspect existing lightweight entry points
- reason about migration approaches
- create/update `OPENAI_MIGRATION_PLAN.md`

## You MUST NOT YET

- implement the Responses migration
- change production Python code
- upgrade packages
- rewrite configuration
- delete Assistants code
- refactor classes
- add frameworks
- create a test suite
- modify Twitch integration
- perform broad dependency modernization

If a live OpenAI call is needed to resolve an important uncertainty during the audit, document the exact small command or use case for me to run. Do not execute the API call yourself.

I am happy to participate in interactive validation because I want to see and understand what the application is doing.

## API execution is user-controlled

Do not make live OpenAI API calls yourself during this audit or during later implementation/validation unless I explicitly tell you to do so.

When validation requires invoking OpenAI, prepare the smallest useful command, class `main()` invocation, shell command, or application action and ask me to run it. I will execute API-triggering steps myself and provide the resulting output/errors back to you.

This includes, but is not limited to:

- running Python modules or `main()` functions that invoke OpenAI
- starting the bot when startup will invoke OpenAI
- executing shell commands/scripts that send OpenAI requests
- triggering Responses, function calls, Structured Outputs, TTS, or other OpenAI endpoints
- performing "quick" or "harmless" API smoke tests on my behalf

You may freely run non-API inspection commands, static code analysis, repository searches, imports/version checks, and other local operations that do not send requests to OpenAI.

For each migration milestone, tell me exactly what to run and what result/error to return to you. Treat me as the operator for all live API validation until I explicitly change this rule.
---

# 28. FINAL RESPONSE AFTER THE AUDIT

Once `OPENAI_MIGRATION_PLAN.md` has been written:

Do **not** paste the entire plan into the Codex conversation.

Give me only a compact summary containing:

1. the path of the Markdown artifact created/updated
2. the most important architectural finding
3. the recommended state strategy
4. the headline tool/Structured Output finding
5. the proposed first implementation milestone
6. any blocker that requires my decision

Then stop.

Do not begin implementation until I explicitly tell you to proceed with a milestone.

---

# 29. SUCCESS CRITERIA FOR THIS AUDIT

This audit is successful if, after reading the resulting Markdown, another coding session can immediately understand:

- why the application currently fails
- every important OpenAI integration point
- which old concepts disappear rather than being recreated
- how existing requests/queues remain intact
- what happens to each tool
- how structured output is handled
- whether conversation state is actually needed
- which current models should be considered and why
- what dependencies require changing
- what files are likely to change
- how migration is divided into resumable milestones
- exactly what to implement first
- exactly how I can manually verify each milestone
- what was deliberately deferred

The ultimate philosophy is:

> Restore the author's application, not redesign it for the author.
