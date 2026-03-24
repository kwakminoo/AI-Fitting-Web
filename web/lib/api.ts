const DEFAULT_BASE = "http://localhost:8000";

export function getApiBase(): string {
  if (typeof process.env.NEXT_PUBLIC_API_URL === "string") {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  return DEFAULT_BASE;
}

export type TryOnResponse = {
  result_url: string;
};

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : String(x)))
      .join(", ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: string }).message);
  }
  return "요청에 실패했습니다.";
}

export async function postTryOn(
  userFile: File,
  clothFile: File,
  signal?: AbortSignal,
): Promise<TryOnResponse> {
  const base = getApiBase();
  const body = new FormData();
  body.append("user_img", userFile);
  body.append("cloth_img", clothFile);

  const res = await fetch(`${base}/api/try-on`, {
    method: "POST",
    body,
    signal,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const err = (await res.json()) as { detail?: unknown };
      if (err.detail !== undefined) message = formatDetail(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }

  return (await res.json()) as TryOnResponse;
}
