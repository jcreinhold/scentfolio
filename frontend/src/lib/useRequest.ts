import { useEffect, useReducer, useState } from "react";

type Result<T> =
  { status: "ready"; data: T } | { status: "failed"; error: string };

type Read<T> = (signal: AbortSignal) => Promise<T>;

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

/** Only the current read may publish a result. Keep read stable until its inputs change. */
export function useRequest<T>(read: Read<T>) {
  const [revision, reload] = useReducer((value: number) => value + 1, 0);
  const [snapshot, setSnapshot] = useState<{
    read: Read<T>;
    revision: number;
    result: Result<T>;
  }>();

  useEffect(() => {
    const controller = new AbortController();
    const publish = (result: Result<T>) => {
      if (!controller.signal.aborted) {
        setSnapshot({ read, revision, result });
      }
    };

    read(controller.signal).then(
      (data) => publish({ status: "ready", data }),
      (error) =>
        publish({
          status: "failed",
          error: errorMessage(error, "Request failed"),
        }),
    );
    return () => controller.abort();
  }, [read, revision]);

  const result =
    snapshot?.read === read && snapshot.revision === revision
      ? snapshot.result
      : { status: "loading" as const };
  return { result, reload };
}
