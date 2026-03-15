import { useEffect, useState } from "react";

export function useElapsedMs(active: boolean, tickMs: number = 1000): number {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsedMs(0);
      return;
    }

    const start = performance.now();
    setElapsedMs(0);
    const intervalId = window.setInterval(() => {
      setElapsedMs(performance.now() - start);
    }, tickMs);

    return () => window.clearInterval(intervalId);
  }, [active, tickMs]);

  return elapsedMs;
}

export function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
