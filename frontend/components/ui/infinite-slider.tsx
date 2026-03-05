"use client";

import React from "react";

type InfiniteSliderProps = {
  children: React.ReactNode;
  gap?: number;
  reverse?: boolean;
  speed?: number;
  speedOnHover?: number;
  /** Number of copies for seamless loop (2 = -50%, 3 = -33.33%). More copies = longer strip, all items visible. */
  copies?: number;
  className?: string;
};

/**
 * Infinite horizontal slider (marquee). Duplicates children for seamless loop.
 */
export function InfiniteSlider({
  children,
  gap = 24,
  reverse = false,
  speed = 80,
  speedOnHover,
  copies = 2,
  className = "",
}: InfiniteSliderProps) {
  const [duration, setDuration] = React.useState(speed);
  const animName = copies === 3 ? "infinite-slider-scroll-3" : "infinite-slider-scroll";

  const style: React.CSSProperties = {
    display: "flex",
    width: "max-content",
    gap: `${gap}px`,
    animation: `${animName} ${duration}s linear infinite`,
    animationDirection: reverse ? "reverse" : "normal",
    willChange: "transform",
  };

  return (
    <div className={className}>
      <div style={style}>
        {Array.from({ length: copies }, (_, i) => (
          <React.Fragment key={i}>{children}</React.Fragment>
        ))}
      </div>
    </div>
  );
}
