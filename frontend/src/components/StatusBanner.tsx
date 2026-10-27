import { ApiError } from "../api/client";

export function ErrorBanner({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg =
    error instanceof ApiError
      ? `${error.status}: ${error.message}`
      : error instanceof Error
        ? error.message
        : "Unknown error";
  return (
    <div className="banner error" role="alert">
      <span>Could not load data. {msg}</span>
      {onRetry && (
        <button className="btn" type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function WarnBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="banner warn" role="status">
      {children}
    </div>
  );
}

export function Skeleton({ label }: { label: string }) {
  return <div className="skeleton" role="status" aria-label={label} />;
}
