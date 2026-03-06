"use client";

import { AnimatePresence, motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { TextShimmer } from "./TextShimmer";

interface AnalysisStepDisplayProps {
  step: string;
  /** Use "button" when rendered inside the dark analyze button (black text + light shimmer) */
  variant?: "default" | "button";
  className?: string;
  framerProps?: HTMLMotionProps<"div">;
}

const defaultFramerProps: HTMLMotionProps<"div"> = {
  initial: { opacity: 0, y: -12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 12 },
  transition: { duration: 0.25, ease: "easeOut" },
};

export function AnalysisStepDisplay({
  step,
  variant = "default",
  className,
  framerProps = defaultFramerProps,
}: AnalysisStepDisplayProps) {
  const isEmpty = !step || !step.trim();

  return (
    <div className={cn("overflow-hidden py-0.5 min-h-[1.5rem] flex items-center justify-center w-full min-w-0", className)}>
      <AnimatePresence mode="wait">
        {isEmpty ? (
          <motion.span
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            className="text-sm text-current"
          >
            …
          </motion.span>
        ) : (
          <motion.div
            key={step}
            className="flex items-center justify-center w-full min-w-0 text-center"
            {...framerProps}
          >
            {variant === "button" ? (
              <TextShimmer
                as="span"
                duration={2}
                spread={2}
                className={cn(
                  "text-sm font-medium whitespace-normal break-words",
                  "[--base-color:#0c0c0c] [--base-gradient-color:#ffffff]",
                  "dark:[--base-color:#0c0c0c] dark:[--base-gradient-color:#e4e4e7]"
                )}
              >
                {step}
              </TextShimmer>
            ) : (
              <TextShimmer as="span" duration={2} spread={2} className="text-sm whitespace-normal break-words">
                {step}
              </TextShimmer>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
