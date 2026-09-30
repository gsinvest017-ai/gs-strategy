import React from "react";
import { renderToString } from "react-dom/server";
import { expect, it } from "vitest";
import { GraphNode, Drawer } from "./main";

it.each(["__proto__", "constructor"])("C4 renders node and drawer for reserved id %s", (id) => {
  const data = {
    node: { id, type: "data.test", params: {} },
    type: { inputs: {}, outputs: {}, params: {} },
  };
  expect(renderToString(React.createElement(GraphNode, {id, data}))).toContain(`<strong>${id}</strong>`);
  expect(renderToString(React.createElement(Drawer, {id}))).toContain(`<h2>${id}</h2>`);
});
