import { NextResponse } from "next/server";

const FALLBACK_BACKEND = "http://127.0.0.1:8000";

function resolveBackendBase(): string {
  const raw =
    process.env.BACKEND_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    FALLBACK_BACKEND;
  return raw.replace(/\/$/, "");
}

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const backendBase = resolveBackendBase();
    const upstream = await fetch(`${backendBase}/api/try-on`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });

    const text = await upstream.text();
    const contentType = upstream.headers.get("content-type") || "application/json";
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "content-type": contentType,
      },
    });
  } catch (e) {
    const message =
      e instanceof Error ? e.message : "백엔드 연결에 실패했습니다.";
    return NextResponse.json(
      { detail: `백엔드 연결 실패: ${message}` },
      { status: 502 },
    );
  }
}
