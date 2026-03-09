/**
 * Datafast goal tracking for conversion funnel.
 * See https://datafa.st/docs/custom-goals
 * Goal names: lowercase, numbers, underscores, hyphens, max 64 chars.
 * Params: max 10, values max 255 chars.
 */
export function trackDatafastGoal(
  goalName: string,
  params?: Record<string, string>
): void {
  if (typeof window === "undefined") return;
  const fn = (window as unknown as { datafast?: (name: string, p?: object) => void }).datafast;
  if (typeof fn !== "function") return;
  if (params && Object.keys(params).length > 0) {
    fn(goalName, params);
  } else {
    fn(goalName);
  }
}
