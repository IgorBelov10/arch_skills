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

1. **Understand the scope.** Figure out from the conversation (or a single
   clarifying question if genuinely unclear) which components exist and how
   they relate: microservices, databases, load balancers/gateways, Kafka
   topics or other queues, caches, external/3rd-party systems, and clients.
   If the user already described their system in this conversation or in a
   file, use that — don't re-ask for things you already know.

2. **Read `references/styles.md`** before drawing anything. It defines the
   exact shape/color/style string to use for each component type, how to
   draw system boundaries, edge label conventions (REST-style
   `METHOD /path` for sync calls, `publishes:`/`consumes: topic.name` for
   Kafka), and the REST API provided/consumed notation (lollipop & socket —
   see below). Reuse these exactly — don't invent new colors/shapes ad hoc.

3. **Build the XML directly** (don't just copy the template's example
   content — replace it with the user's actual system). `assets/template.drawio`
   is a working example you can view for structural reference: system
   boundary rectangle, microservices, DBs, an API gateway, a Kafka topic,
   an external system, sync REST edges, and async pub/sub edges.
   `scripts/check_overlap.py` is the layout validator used in step 5.

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

4. **Keep it a sketch, not a spec.** Per component: name only, no internal
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

5. **Validate before delivering — two checks, both mandatory:**
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

## Avoiding overlaps and edge crossings in the first place (do
