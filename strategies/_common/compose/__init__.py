"""Compositional research workflow on top of the Live Strategy Graph.

``types``    parametric port types and the edge-compatibility rule
``diagram``  ``>>`` / ``@`` string-diagram DSL that builds graph documents
``pit``      point-in-time guards: model knowledge cutoffs, document knowledge time
``llm``      hot-swappable OpenAI-compatible model calls with CoT capture and call cache
``walkforward``  anchored/rolling walk-forward with nested selection (vector futures engine)
``replay``   per-decision replay frames for the UI
"""
