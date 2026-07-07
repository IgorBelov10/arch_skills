# Visual vocabulary for architecture sketches

This is a fixed, simplified "UML-like" notation for system/component sketches,
drawn in draw.io's **hand-drawn "Sketch" style** (rough.js rendering — the
same thing the "Sketch" checkbox in the Style panel turns on). Reuse these
exact `style` strings so every diagram looks consistent.

All values below assume an `mxCell` with `vertex="1" parent="1"` (or parent =
a boundary id if you choose to nest — see "System boundaries" below).

## The hand-drawn look

Every shape and every edge gets `sketch=1;` in its style — this switches
draw.io's renderer to hand-drawn (rough.js) strokes instead of clean vector
lines. Tune it with (optional, defaults are fine to start with):
- `hachureGap=4;` — spacing of hatch lines when a hachure fill is used
- `jiggle=2;` — how "wobbly" the hand-drawn line looks (0 = barely, higher = shakier)
- `curveFitting=1;` — smooths the rough strokes slightly

When a shape uses a **hachure fill** (see microservices below), add
`fillStyle=hachure;` alongside a `fillColor`. `fillStyle` can also be
`cross-hatch` or `solid` if you want to vary the texture for another
category later — just record any new variant in the table below.

## Component shapes

| Component type | style string | typical size (w x h) |
|---|---|---|
| **Microservice — core/business logic (default)** | `shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#333333;sketch=1;jiggle=2;fontSize=12;` | 160x70 |
| **Microservice — utility/infra (auth, notifications, scheduling, etc.)** | same as above **plus** `fillColor=<category color>;fillStyle=hachure;hachureGap=4;` — keep `fillStyle=hachure` constant across all utility services, vary only `fillColor` per category so each utility type is recognizable at a glance | 160x70 |
| **Database** | `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#d5e8d4;strokeColor=#82b366;sketch=1;jiggle=2;fontSize=12;` | 100x80 |
| **Load balancer / API gateway** | `rhombus;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#333333;sketch=1;jiggle=2;fontSize=12;` | 120x80 |
| **Kafka topic / queue** | `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;direction=north;sketch=1;jiggle=2;fontSize=11;` — `direction=north` rotates the cylinder 90° so it lies on its side (distinguishes it from the upright DB cylinder). If it comes out rotated the wrong way, swap to `direction=south` — the important thing is it ends up horizontal, not upright. | 110x60 |
| **Cache (Redis etc.)** | `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#e1d5e7;strokeColor=#9673a6;sketch=1;jiggle=2;fontSize=12;` | 100x70 |
| **External system / 3rd party** | `ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;sketch=1;jiggle=2;fontSize=12;` — keep it visibly **wider than tall** (e.g. 150x70) so it's never confused with the diamond LB/gateway shape above | 150x70 |
| **Client / UI — technical component (browser, mobile app, desktop app)** | `rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;sketch=1;jiggle=2;fontSize=12;` | 140x60 |
| **Actor — human role (user, admin, external person)** | `verticalLabelPosition=bottom;html=1;outlineConnect=0;shape=umlActor;verticalAlign=top;strokeColor=#333333;fillColor=none;sketch=1;jiggle=2;fontSize=12;` — the standard UML actor stick figure; use it instead of the client box whenever the diagram needs to show a *person/role*, not a piece of software | 30x60 |

Use the actor shape only for actual human roles. Use the client box for the
technical artifact (the app/browser itself). A diagram can have both, e.g.
`Customer (actor) → Mobile App (client box) → API Gateway`, if that
distinction matters for the sketch.

Only invent a new shape/color if none of the above fit — and if you do, add
it to this table so future diagrams stay consistent.

## REST API interfaces (provided vs. consumed — lollipop & socket)

When a service **exposes** a REST API, give it a short stub edge ending in
a small transparent (unfilled) circle — the "lollipop." When another
service **consumes** that API, draw its own edge reaching toward that
circle, ending in a half-circle "socket" that almost touches the lollipop
but stops just short of it, leaving a visible gap. Both `circle` and
`halfCircle` are real built-in `endArrow` values in draw.io — this isn't a
custom shape.

**Lollipop (provider) — one per service that exposes a REST API:**
- An edge with `source` = the service's id and **no `target` cell** —
  instead give it a floating end point via a child
  `<mxPoint x="..." y="..." as="targetPoint" />` inside the edge's
  `mxGeometry`.
- Style: `edgeStyle=none;html=1;endArrow=circle;endFill=0;endSize=7;startArrow=none;strokeColor=#333333;sketch=1;jiggle=1;`
- Geometry: pick a direction pointing into open space near the service
  (up, down, left, or right — whichever side has room), and make the stub
  **~30px long**: if the exit point on the service is `(Px, Py)`, the
  floating tip is `(Px, Py - 30)` for "up", `(Px, Py + 30)` for "down",
  etc. Treat this tip point like any other obstacle-check target when
  planning the stub's own short path (it's usually short enough that this
  is trivial).
- **Label the method(s) next to the lollipop itself, not on the socket
  edge.** Add a separate plain-text vertex
  (`style="text;html=1;align=left;verticalAlign=middle;fontSize=11;fontColor=#333333;sketch=1;"`)
  positioned just beside the tip (e.g. offset ~15px to the side, sized
  ~150x20), with the method(s) as its value — `GET /inventory`, or several
  lines if the same interface exposes more than one method. This is the
  one place that documents what the interface offers; it stays put
  regardless of how many consumers connect sockets to it. Check it against
  the overlap checker like any other component.

**Socket (consumer) — one edge per service that calls that REST API:**
- An edge with `source` = the consuming service's id and, again, **no
  `target` cell** — a floating `<mxPoint as="targetPoint">`. **Leave it
  unlabeled** (no `value`) — the method lives on the lollipop's text block,
  not here, so multiple consumers of the same interface don't repeat or
  (worse) drift out of sync with each other.
- Style: `edgeStyle=orthogonalEdgeStyle;html=1;endArrow=halfCircle;endFill=0;endSize=10;startArrow=none;strokeColor=#333333;sketch=1;jiggle=1;`
- **Critical geometry rule — the gap:** the socket's target point must sit
  on the *far side* of the lollipop tip from the provider — i.e.
  continuing outward along the same line, not between the provider and
  its own tip. With a lollipop tip at `(Px, Py - 30)` (stub pointing up),
  the socket's target point is `(Px, Py - 30 - 2)` = 2px *further* in
  the same outward direction — keep this gap minimal (~2px), just enough
  that the circle and half-circle read as two distinct marks rather than
  one touching shape. That gap is the only thing drawn between them: the
  socket's line never overlaps the lollipop's own stub. Route the rest of
  the socket edge with waypoints (per the edge-crossing rules above) so
  its *last* segment approaches straight along this same axis into the
  gap point.
- If several services consume the same API, give each its own socket edge
  aimed at the same lollipop tip (from whatever clear angle each consumer
  can reach it from), all stopping ~2px short with their own gap.

See `assets/template.drawio` for a fully worked, verified-clear example
(a provider and a consumer with the lollipop/socket pair, plus the
waypoint routing that gets the socket there cleanly).

## System boundaries

Draw every logical system/bounded-context as a plain dashed rectangle placed
**behind** its members (put its `mxCell` earlier in the XML than the
components inside it, so z-order puts it in back). Do NOT use draw.io
"container" mode (`container=1`) — it forces child coordinates to become
relative to the parent and is easy to get wrong. Plain absolute coordinates
for everything, with the boundary just drawn underneath, is far more robust.

```
style="rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;dashed=1;verticalAlign=top;align=left;fontStyle=1;spacingLeft=8;spacingTop=6;fontSize=13;sketch=1;jiggle=2;"
```

Size the rectangle to comfortably enclose its children with ~30-40px margin
on every side. Label it with the system/bounded-context name (e.g. "Order
System", "Billing Context").

## Edges (calls between components)

Default style for synchronous calls (REST/gRPC):
```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;fontSize=11;sketch=1;jiggle=2;
```
Label with the REST-style method + path only, no request/response body
details, e.g.:
- `GET /orders/{id}`
- `POST /payments`
- `PUT /orders/{id}/status`

For asynchronous / event-driven edges (publish or consume to/from a Kafka
topic), use a dashed open-arrow edge so sync vs async is visually distinct:
```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;fontSize=11;sketch=1;jiggle=2;
```
Label these with just the topic/event name, not payload schema, e.g.
`publishes: order.created` or `consumes: order.created`.

Keep every edge label short (one line). If a relationship needs more
explanation than fits on one line, it's too detailed for a sketch — leave it
out.

## Layout conventions

- Grid step ~20-40px; snap x/y to multiples of 20.
- Left-to-right or top-to-bottom flow matching request direction (client on
  the left/top).
- Leave 40-60px gaps between sibling components so edges don't overlap boxes.
- Don't cram more than ~15-20 components into a single sketch — split into
  multiple diagrams (e.g. by bounded context) if the system is bigger than
  that. A sketch that needs scrolling to read has failed its job.
- Font size 12 for component labels, 11 for edge labels; nothing smaller.

## ID conventions

Give every `mxCell` a short, readable, unique id (`gw1`, `svcOrder`,
`dbOrders`, `topicOrderEvents`, `sysOrder`, `e1`, `e2`, ...) rather than
random hashes — makes the XML diffable and easy to hand-edit later.
