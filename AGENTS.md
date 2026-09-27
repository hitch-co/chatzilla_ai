# Development Guidelines

## Preserve before improving

This is a small personal project whose existing structure is intentionally easy to read and reason about.

Preserve the current architecture, file layout, naming, control flow, and coding style extremely aggressively.

Prefer:

```text
existing working concept
    ↓
small functional or compatibility change
    ↓
working updated equivalent
```

Do not turn a small change into:

```text
existing working concept
    ↓
new abstraction
    ↓
new manager/service
    ↓
new state-management layer
    ↓
new architecture
```

If existing code can reasonably be adapted in place, adapt it in place.

Assume existing structure is intentional unless explicitly told otherwise. Being able to open the project months later and recognize and understand the code is more important than architectural purity.

## Keep diffs small

Prefer the smallest change that produces the required functional behavior.

- Edit an existing function or small block rather than restructuring surrounding code.
- Preserve existing naming and control-flow shape where practical.
- Do not rewrite whole functions when a few lines can accomplish the change.
- Do not reformat, rename, reorder, or clean up unrelated code.
- Do not move files or reorganize modules unless explicitly requested.
- Do not bundle opportunistic cleanup into functional changes.
- Leave functional but imperfect unrelated code alone.

Code changes should be easy to compare against the previous version and understand line-by-line.

## Do not redesign or professionalize the project

Do not introduce new:

- classes
- managers
- services
- registries
- factories
- state machines
- dependency-injection layers
- exception hierarchies
- configuration frameworks
- orchestration frameworks
- persistence systems
- internal frameworks or "systems around systems"

Do not refactor simply because:

- responsibilities could be reorganized
- a class could have a better name
- newer Python idioms exist
- a framework could reduce boilerplate
- code could be more scalable or "enterprise"
- state could be formalized
- error handling could be centralized
- retries could be generalized
- models could be converted to Pydantic
- an SDK or agent framework provides a newer architectural pattern
- LangChain, an Agent SDK, or another abstraction could replace existing logic

Use new architectural machinery only when explicitly requested or when the requested functionality is genuinely infeasible within the existing structure.

## Prefer straightforward code over abstraction

Reuse an existing function when the exact same logic already has an obvious home.

Avoid copying substantial identical logic into multiple places when a simple existing function call solves the problem.

At the same time, do not create an abstraction layer merely to eliminate a small amount of duplication.

Prefer explicit, local, readable orchestration over generalized machinery.

A little duplication is acceptable when the alternative would make the code harder to follow.

## Keep state minimal

Bias toward the least stateful implementation that reproduces the required behavior.

Do not introduce persistent state, lifecycle management, databases, tracking objects, state machines, response registries, or conversation-management systems merely because an API or library supports them.

If a request already contains the information required to perform its task, prefer handling it directly rather than creating additional application state.

Do not preserve or create state solely for hypothetical future requirements.

## Keep error handling minimal and practical

This is a localhost personal project, not a production service.

Normal Python exceptions and tracebacks during development are useful and acceptable.

Handle immediate, realistic failure modes, especially known failures from external services, but do not build production-grade resilience around ordinary project code.

Do not introduce:

- generalized retry frameworks
- circuit breakers
- state-recovery systems
- extensive fallback chains
- elaborate validation frameworks
- defensive checks around every possible state
- logging infrastructure projects
- speculative recovery behavior
- broad try/except wrappers that hide useful errors

Do not add checks for:

- theoretically possible states
- highly improbable states
- edge cases that have not actually mattered
- "just in case" conditions
- hypothetical malformed internal state
- scenarios whose only justification is that they might happen someday

If an uncommon problem actually occurs, it can be handled when it becomes a real problem.

Existing overly complicated error handling may be simplified or removed when it directly interferes with a requested change, but do not perform unrelated cleanup.

## Match the existing project

Match existing:

- naming conventions
- file organization
- function style
- control-flow patterns
- configuration patterns
- object usage
- calling conventions

Do not modernize code merely because another Python style would be more conventional.

When several valid implementations exist, prefer the one that looks most like the surrounding project.

## Comments should be rare

Do not add narration comments that simply describe what the code is doing.

Prefer readable code and existing names.

Add a comment only in the rare case where an unusual implementation decision has important intent that would otherwise be difficult to infer.

## Do not expand testing proactively

Do not add new tests unless explicitly requested.

Do not create tests simply because:

- new behavior was added
- similar tests already exist
- coverage could be improved
- a change would normally warrant a unit test in a production project

Existing tests may be updated when a requested functional change directly requires it, but do not broaden the test suite as part of unrelated work.

## Stay within the requested scope

Implement the requested behavior and stop.

Do not use a task as an opportunity to:

- clean nearby code
- address unrelated technical debt
- improve architecture
- add resilience
- normalize style
- prepare for hypothetical future features
- introduce infrastructure that might be useful later

When unrelated code looks ugly but works, leave it alone.

When a broader change appears genuinely necessary, explain why before expanding the scope.
