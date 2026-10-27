import { useId, useState } from "react";
import type { CutoffPreset } from "../api/types";
import { CUTOFF_RE } from "../state/urlState";

interface Props {
  value: string;
  presets: CutoffPreset[];
  onChange: (cutoff: string) => void;
  label?: string;
}

/** Market presets plus a free-entry time. Always UK local time on the decision date. */
export default function CutoffPicker({ value, presets, onChange, label = "Decision cutoff (UK time)" }: Props) {
  const id = useId();
  const isPreset = presets.some((p) => p.time === value);
  const [custom, setCustom] = useState(!isPreset);
  return (
    <div className="field">
      <span className="label" id={`${id}-label`}>
        {label}
      </span>
      <div role="group" aria-labelledby={`${id}-label`} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div className="segmented">
          {presets.map((p) => (
            <button
              key={p.key}
              type="button"
              aria-pressed={!custom && value === p.time}
              title={p.label}
              onClick={() => {
                setCustom(false);
                onChange(p.time);
              }}
            >
              {p.key.toUpperCase()} {p.time}
            </button>
          ))}
          <button type="button" aria-pressed={custom} onClick={() => setCustom(true)}>
            Custom
          </button>
        </div>
        {custom && (
          <input
            type="time"
            aria-label="Custom cutoff time"
            value={value}
            step={60}
            onChange={(e) => {
              if (CUTOFF_RE.test(e.target.value)) onChange(e.target.value);
            }}
          />
        )}
      </div>
    </div>
  );
}
