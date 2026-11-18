/**
 * Run `fn` over `items` with at most `limit` calls in flight at once.
 * Results are returned in input order. Each result is a settled outcome so one
 * rejection never sinks the batch: `{ ok: true, value }` or `{ ok: false, error }`.
 */
export type Settled<T> = { ok: true; value: T } | { ok: false; error: unknown };

export async function mapPool<I, O>(
  items: I[],
  limit: number,
  fn: (item: I, index: number) => Promise<O>,
  onSettle?: (index: number, result: Settled<O>) => void,
): Promise<Settled<O>[]> {
  const results = new Array<Settled<O>>(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      let settled: Settled<O>;
      try {
        settled = { ok: true, value: await fn(items[i], i) };
      } catch (error) {
        settled = { ok: false, error };
      }
      results[i] = settled;
      onSettle?.(i, settled);
    }
  };
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, worker),
  );
  return results;
}
