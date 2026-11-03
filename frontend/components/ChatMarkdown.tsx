"use client";

import type { ReactNode } from "react";

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function isListLine(line: string): boolean {
  return /^\s*(?:[-*]|\d+[.)])\s+/.test(line);
}

function stripListMarker(line: string): string {
  return line.replace(/^\s*(?:[-*]|\d+[.)])\s+/, "");
}

function isHeading(line: string): boolean {
  return /^\s*#{1,3}\s+\S/.test(line);
}

export function ChatMarkdown({ text }: { text: string }) {
  const normalized = (text || "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return null;
  const blocks = normalized.split(/\n{2,}/);

  return (
    <div className="space-y-2.5 text-[13px] leading-relaxed text-zinc-200">
      {blocks.map((block, i) => {
        const lines = block.split("\n").filter((line) => line.trim() !== "");
        if (lines.length === 0) return null;

        if (lines.length >= 1 && lines.every(isListLine)) {
          return (
            <ul key={i} className="list-disc space-y-1 pl-4 marker:text-[#00ffe8]">
              {lines.map((line, j) => (
                <li key={j}>{renderInline(stripListMarker(line))}</li>
              ))}
            </ul>
          );
        }

        if (lines.length === 1 && isHeading(lines[0])) {
          return (
            <p key={i} className="font-semibold text-white">
              {renderInline(lines[0].replace(/^\s*#{1,3}\s+/, ""))}
            </p>
          );
        }

        return (
          <p key={i}>
            {lines.map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {isHeading(line) ? (
                  <strong className="font-semibold text-white">
                    {renderInline(line.replace(/^\s*#{1,3}\s+/, ""))}
                  </strong>
                ) : isListLine(line) ? (
                  <>• {renderInline(stripListMarker(line))}</>
                ) : (
                  renderInline(line)
                )}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
