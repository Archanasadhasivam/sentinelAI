"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FixturePayload } from "@/lib/types";
import { Zap } from "lucide-react";

export function AttackPresetMenu({ onSelect }: { onSelect: (text: string) => void }) {
  const [fixtures, setFixtures] = useState<FixturePayload[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.getFixtures().then((res) => setFixtures(res.fixtures)).catch(() => setFixtures([]));
  }, []);

  const grouped = fixtures.reduce<Record<string, FixturePayload[]>>((acc, f) => {
    (acc[f.category] ??= []).push(f);
    return acc;
  }, {});

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-sm border border-border px-3 py-1.5 text-sm hover:bg-surface-hover"
      >
        <Zap size={14} className="text-warning" />
        Attack presets
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-96 max-h-96 overflow-y-auto rounded-sm border border-border bg-surface z-30">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <div className="flex items-center gap-2 px-3 py-1.5 text-[11px] text-muted-foreground bg-surface-hover sticky top-0">
                <span className="inline-block w-[3px] h-3 bg-primary/70 shrink-0" aria-hidden />
                {category.replaceAll("_", " ")}
              </div>
              {items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelect(item.text);
                    setOpen(false);
                  }}
                  className="block w-full text-left px-3 py-2 text-sm hover:bg-surface-hover border-b border-border/50"
                >
                  <div className="font-medium">{item.label}</div>
                  <div className="text-xs text-muted-foreground truncate">{item.text}</div>
                </button>
              ))}
            </div>
          ))}
          {fixtures.length === 0 && (
            <div className="p-3 text-sm text-muted-foreground">
              Couldn&apos;t load presets — is the backend running?
            </div>
          )}
        </div>
      )}
    </div>
  );
}
