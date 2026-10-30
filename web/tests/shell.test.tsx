import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";

import { Divider } from "@/components/ui/divider";
import { Tabs } from "@/components/ui/tabs";
import { getApiKey, isKeyRemembered, setApiKey } from "@/lib/settings";

function Harness() {
  const [size, setSize] = useState(140);
  return (
    <Divider
      label="Resize sidebar"
      size={size}
      min={48}
      max={240}
      onResize={(v) => setSize(Math.min(240, Math.max(48, v)))}
      onReset={() => setSize(140)}
    />
  );
}

test("divider resizes with arrow keys and resets on double-click", () => {
  render(<Harness />);
  const sep = screen.getByRole("separator", { name: "Resize sidebar" });
  fireEvent.keyDown(sep, { key: "ArrowRight" });
  expect(sep).toHaveAttribute("aria-valuenow", "156");
  fireEvent.keyDown(sep, { key: "Home" });
  expect(sep).toHaveAttribute("aria-valuenow", "48");
  fireEvent.doubleClick(sep);
  expect(sep).toHaveAttribute("aria-valuenow", "140");
});

test("tabs move selection with arrow keys", () => {
  const onChange = vi.fn();
  render(
    <Tabs
      label="Mode"
      value="a"
      options={[
        { value: "a", label: "A" },
        { value: "b", label: "B" },
      ]}
      onChange={onChange}
    />,
  );
  fireEvent.keyDown(screen.getByRole("radio", { name: "A" }), { key: "ArrowRight" });
  expect(onChange).toHaveBeenCalledWith("b");
});

test("api key is session-only unless remembered", () => {
  setApiKey("k1", false);
  expect(getApiKey()).toBe("k1");
  expect(isKeyRemembered()).toBe(false);
  setApiKey("k2", true);
  expect(window.sessionStorage.getItem("behique.apiKey")).toBeNull();
  expect(getApiKey()).toBe("k2");
  setApiKey("", true);
  expect(getApiKey()).toBe("");
});
