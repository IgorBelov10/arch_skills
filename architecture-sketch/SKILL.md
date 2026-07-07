---
name: architecture-sketch
description: Use this skill whenever the user wants a software/system architecture sketch, diagram, or schema — e.g. "нарисуй архитектуру", "накидай схему сервисов", "draw the architecture", "component diagram", "system diagram", or anything showing microservices, databases, load balancers/gateways, message queues/Kafka topics, or system boundaries. Always produce output as a real .drawio (diagrams.net / mxGraph) file the user can open and keep editing in draw.io — never a static image or an inline text description alone. Trigger this even if the user doesn't say "drawio" explicitly, as long as they want a visual sketch of services/components/systems rather than prose.
---

# Architecture Sketch (draw.io)

Produces lightweight, consistent architecture sketches as real `.drawio`
files (the format used by diagrams.net / draw.io), using a fixed, simplified
"UML-like" notation. These are **sketches**, not exhaustive documentation:
they show system boundaries and components and how they call each other —
not database schemas, method bodies, or config.

## Workflow

1. **Understand the scope — skip the interview if this is already answered.**
   If the user already described their system in this conversation or in a
   file (services, DBs, how they connect), use that directly and skip to
   step 5. Otherwise run the interview below.

2. **Interview, part A — scope & categories (buttons).** One
   `ask_user_input_v0` call, up to 3 questions:
   - Scope: "high-level overview" / "one bounded context in detail" / "the
     whole system as-is"
   - Component categories present (multi-select): microservices / databases
     / queues or Kafka topics / external 3rd-party systems / cache / API
     gateway or load balancer
   - Whether to use the provided/consumed REST API notation (lollipop &
     socket): yes / no / decide as we go

3. **Interview, part B — names only (plain text question).** Ask **only**
   for the names of components, grouped **only** by the categories the
   user selected in part A — don't ask about a category they didn't pick,
   and don't ask about functionality yet. Example, if they picked
   microservices + databases + Kafka + gateway:
   > Перечисли имена: микросервисов, баз данных, Kafka-топиков,
   > gateway/LB (если их несколько).
   This is a free-text question, not `ask_user_input_v0` — names and counts
   are too open-ended for buttons.

4. **Interview, part C — per-component profile, iterative.** For each
   component named in part B, in turn:
   1. Draft a profile using the template for its category (below), inferring
      what you reasonably can from the component's name and its stated
      relationships to others named so far — don't leave every field as a
      guess-free blank if the name makes something obvious (e.g. a service
      named "Order Service" plausibly owns an "orders" DB).
   2. Show the draft to the user.
   3. Let them correct or add to it; redraft; show again.
   4. Repeat until the user confirms (e.g. "ОК") — only then move to the
      next component.
   Don't batch all components into one giant question — go one at a time,
   so corrections stay easy to track. Once every component is confirmed,
   proceed to building the diagram (step 6 on).

   **Profile templates per category:**

   - **Microservice:** responsibility (one phrase — what business function
     it owns); type — core/business logic vs. utility/infra (decides
     hachure fill); REST APIs it exposes (`METHOD /path` list, → becomes a
     lollipop); REST APIs of other services it calls (which service, which
     endpoint); Kafka: what it publishes / what it consumes; which DB it
     uses; which external 3rd-party systems it calls.
   - **Database:** which service owns it (normally 1:1). Engine/type is
     optional — only ask if the user cares, it doesn't need to appear on
     the sketch.
   - **Kafka topic:** event/topic name; which service(s) publish; which
     service(s) consume.
   - **API gateway / load balancer:** which services sit behind it
     (routing).
   - **External / 3rd-party system:** which service(s) call it and why, in
     one short phrase.
   - **Cache:** which service uses it.
   - **Client / actor:** which gateway or service it enters the system
     through.

5. **Read `references/styles.md`** before drawing anything. It defines the
   exact shape/color/style string to use for each component type, how to
   draw system boundaries, edge label conventions (REST-style
   `METHOD /path` for sync calls, `publishes:`/`consumes: topic.name` for
   Kafka), and the REST API provided/consumed notation (lollipop & socket —
   see below). Reuse these exactly — don't invent new colors/shapes ad hoc.

6. **Build the XML directly** (don't just copy the template's example
   content — replace it with the user's actual system, informed by the
   confirmed profiles from step 4). `assets/template.drawio`
   is a working example you can view for structural reference: system
   boundary rectangle, microservices, DBs, an API gateway, a Kafka topic,
   an external system, sync REST edges, and async pub/sub edges.
   `scripts/check_overlap.py` is the layout validator used in step 8.

   Key structural rules:
   - Root is `<mxfile><diagram><mxGraphModel><root>`, with `mxCell id="0"`
     and `mxCell id="1" parent="0"` always present first.
   - Every component and boundary is `parent="1"` with **absolute**
     coordinates — do not use draw.io "container" mode
     (no `container=1`), it's more error-prone than it's worth for a sketch.
   - Draw system boundary rectangles *before* the components they contain
     in the XML (so z-order puts them behind).
   - Give every cell a short readable id (`svcOrder`, `dbOrders`,
     `topicOrderEvents`, not random hashes).
   - Edges reference `source`/`target` by those ids and need
     `<mxGeometry relative="1" as="geometry" />`.

7. **Keep it a sketch, not a spec.** Per component: name only, no internal
   detail. Per edge: one-line label only (`GET /orders/{id}`,
   `publishes: order.created`) — never full request/response schemas,
   headers, or payload fields. If the user asks for that level of detail,
   gently note that it stops being a "sketch" and confirm they still want it
   crammed onto the diagram, or suggest splitting into a lower-level
   component diagram.

   If the user specifically asks to show which service **exposes** a REST
   API versus which service(s) **consume** it (as opposed to just "calls"),
   use the lollipop/socket notation from `references/styles.md` instead of
   a plain labeled arrow — it's the dedicated notation for that
   distinction and both `endArrow=circle` and `endArrow=halfCircle` are
   real draw.io arrow types, not a workaround.

8. **Validate before delivering — two checks, both mandatory:**
   - **Well-formed XML:**
     `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.drawio')"`
     (also confirms there are no duplicate `id` values by construction).
   - **Layout check (overlaps *and* edge crossings):**
     `python3 scripts/check_overlap.py file.drawio`
     This flags (a) any pair of components whose bounding boxes overlap
     unintentionally — it correctly ignores a system boundary rectangle
     containing its own components, that overlap is expected — and (b) any
     edge whose path cuts through the bounding box of some *other*
     component it isn't connecting (crossing a system boundary's dashed
     outline is fine and not flagged; passing through a hexagon/cylinder/
     ellipse/etc. that the edge has nothing to do with is not). If it
     reports either kind of problem, **do not deliver the file** — move the
     offending components, or reroute the edge, and re-run the check until
     it reports `OK`. This is not optional: overlapping shapes and edges
     that cut through unrelated components make a sketch unreadable, and
     it's cheap to catch here versus the user finding it after opening the
     file.

   A `.drawio` file that fails either check is worse than no file.

9. **Save to `/mnt/user-data/outputs/<name>.drawio`** and use `present_files`.
   Tell the user briefly what's in it (systems/components shown), not a
   long report — the diagram speaks for itself once opened in draw.io.

## Avoiding overlaps and edge crossings in the first place (do this while laying out, not just after)

- Plan coordinates on a grid before writing XML: decide rows/columns of
  components and leave **at least 40-60px of empty space** between the
  bounding boxes of *any* two sibling components — not just the ones
  expected to be near each other. Gateways, boundaries, and external systems
  routinely get forgotten and end up overlapping neighbors.
- System boundary rectangles must be sized to enclose only their own
  children (with ~30-40px margin). A component that is *not* part of that
  system must stay clearly outside the boundary's box, with a visible gap —
  not flush against or clipping its edge. A box that merely touches or
  overlaps a boundary it doesn't belong to is exactly the bug the overlap
  checker exists to catch.
- **Arrange fan-out as a hub-and-spoke, not a row a line has to reach past.**
  If one component (e.g. a gateway) calls several others, put those targets
  in a row directly on the far side of the hub, centered on it, rather than
  scattered so that the path to a farther target grazes a nearer one. A
  straight (or right-angled) line from the hub to each target should never
  need to skim past a target that isn't the one it's headed to.
- Keep call chains in clean vertical/horizontal lanes where possible (e.g. a
  service directly above its own database) rather than diagonal paths
  crossing other lanes — diagonals are what usually clip a neighboring box.
- **Any edge whose source and target don't share the same x or y needs
  explicit waypoints — this is not optional, and the checker alone is not
  enough.** draw.io's real auto-router does not draw a straight line
  between two floating components; it typically exits the source
  horizontally at the source's own y-level toward the target, then turns.
  That means a "diagonal" edge routinely clips a sibling component that
  happens to sit at the source's height, even when a straight-line
  approximation between the two centers looks perfectly clear. Concretely:
  for every edge where `source.x ≠ target.x` and `source.y ≠ target.y`,
  add an explicit `<Array as="points">` with 1-2 `<mxPoint>` waypoints that
  route it through a verified-clear gap (e.g. down through the empty space
  between two neighboring components, then across, then down/up into the
  target) — don't leave it to auto-routing. The layout checker walks these
  waypoints when present; without them it can only fall back to a
  straight-line approximation, which is known to under-report this exact
  failure mode.
- When components are arranged in a grid (e.g. several microservices each
  with their own DB below them), compute each column's x from the previous
  column's `x + width + gap` rather than eyeballing round numbers —
  eyeballed coordinates are the most common source of overlap.
- If the checker reports a problem, don't just nudge by a few pixels —
  recompute that component's position from its neighbors' actual bounding
  boxes so the fix is robust, not a near-miss that breaks again on the next
  edit.

## When the system is large

If asked to sketch something with many services (roughly >15-20 boxes),
don't cram it into one unreadable diagram. Either:
- Split into multiple `.drawio` files (e.g. one per bounded context, plus one
  high-level overview showing just the system boundaries and their
  connections), or
- Ask the user which context/subset they want first.

## Iterating on an existing sketch

If the user wants to modify a previously generated diagram (add a service,
rename an edge, etc.), read the existing `.drawio` file back, make a
targeted edit (add/modify the relevant `mxCell` elements, keep everything
else untouched), re-run **both** validators (XML well-formedness and
`scripts/check_overlap.py`), and re-save — don't regenerate the whole
diagram from scratch unless asked to. Adding a component near existing ones
is a common way to introduce a fresh overlap, so don't skip the check just
because it's a small edit.
