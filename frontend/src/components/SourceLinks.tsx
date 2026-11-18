export default function SourceLinks({ urls }: { urls: string[] }) {
  const links = new Set<string>();
  for (const value of urls) {
    try {
      const url = new URL(value);
      if (url.protocol === "https:" || url.protocol === "http:") {
        links.add(url.href);
      }
    } catch {
      continue;
    }
  }

  if (links.size === 0) return null;

  return (
    <div className="card-notes" role="group" aria-label="Sources">
      <span>Sources</span>
      {[...links].map((url) => (
        <a
          key={url}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ overflowWrap: "anywhere" }}
        >
          {url}
        </a>
      ))}
    </div>
  );
}
