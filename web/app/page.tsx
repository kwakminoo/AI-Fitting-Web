"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  Download,
  Loader2,
  RefreshCw,
  Share2,
  Shirt,
  Sparkles,
} from "lucide-react";
import { ImageDropzone } from "@/components/ImageDropzone";
import { postTryOn } from "@/lib/api";

type CompareMode = "before" | "after";

export default function Home() {
  const fittingRef = useRef<HTMLElement | null>(null);
  const [userFile, setUserFile] = useState<File | null>(null);
  const [clothFile, setClothFile] = useState<File | null>(null);
  const [userPreviewUrl, setUserPreviewUrl] = useState<string | null>(null);
  const [clothPreviewUrl, setClothPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState<CompareMode>("after");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!userFile) {
      setUserPreviewUrl(null);
      return;
    }
    const u = URL.createObjectURL(userFile);
    setUserPreviewUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [userFile]);

  useEffect(() => {
    if (!clothFile) {
      setClothPreviewUrl(null);
      return;
    }
    const u = URL.createObjectURL(clothFile);
    setClothPreviewUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [clothFile]);

  const canSubmit = Boolean(userFile && clothFile && !loading);

  const handleTryOn = async () => {
    if (!userFile || !clothFile) return;
    setError(null);
    setLoading(true);
    setResultUrl(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    try {
      const { result_url } = await postTryOn(
        userFile,
        clothFile,
        abortRef.current.signal,
      );
      setResultUrl(result_url);
      setCompareMode("after");
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "알 수 없는 오류입니다.");
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const resetToUpload = useCallback(() => {
    setUserFile(null);
    setClothFile(null);
    setResultUrl(null);
    setError(null);
    setCompareMode("after");
    fittingRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const downloadResult = async () => {
    if (!resultUrl) return;
    try {
      const res = await fetch(resultUrl);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `virtual-fitting-${Date.now()}.png`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      window.open(resultUrl, "_blank", "noopener,noreferrer");
    }
  };

  const shareResult = async () => {
    if (!resultUrl) return;
    try {
      const res = await fetch(resultUrl);
      const blob = await res.blob();
      const file = new File([blob], "virtual-fitting.png", { type: blob.type });
      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({
          title: "AI Virtual Fitting Room",
          text: "가상 피팅 결과를 확인해 보세요.",
          files: [file],
        });
        return;
      }
    } catch {
      /* fall through */
    }
    try {
      await navigator.clipboard.writeText(resultUrl);
      alert("결과 이미지 URL이 클립보드에 복사되었습니다.");
    } catch {
      const text = encodeURIComponent("가상 피팅 결과");
      window.open(
        `https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(resultUrl)}`,
        "_blank",
        "noopener,noreferrer",
      );
    }
  };

  const largeSrc =
    compareMode === "before" ? userPreviewUrl : resultUrl || userPreviewUrl;
  const largeAlt =
    compareMode === "before" ? "원본 전신 사진" : "가상 피팅 결과";

  return (
    <div className="flex min-h-full flex-col bg-[var(--background)]">
      <header className="sticky top-0 z-20 border-b border-neutral-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <a
            href="#hero"
            className="font-display text-xl font-semibold tracking-tight text-neutral-900 sm:text-2xl"
          >
            AI Virtual Fitting Room
          </a>
          <nav className="flex items-center gap-6 text-sm font-medium text-neutral-600">
            <a href="#hero" className="transition hover:text-neutral-900">
              소개
            </a>
            <a href="#fitting" className="transition hover:text-neutral-900">
              피팅 시작
            </a>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section
          id="hero"
          className="border-b border-neutral-200 bg-white px-4 py-16 sm:px-6 sm:py-24"
        >
          <div className="mx-auto max-w-3xl text-center">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.25em] text-neutral-400">
              Virtual try-on
            </p>
            <h1 className="font-display text-4xl font-semibold leading-tight text-neutral-900 sm:text-5xl md:text-6xl">
              구매 전에,
              <br />
              내게 어울리는지 미리 입어 보세요
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-neutral-600">
              정면 전신 사진과 옷(또는 모델 착용) 이미지를 올리면 AI가 옷을
              합성해 드립니다. 화이트 톤의 깔끔한 공간에서 패션 잡지처럼 결과를
              감상해 보세요.
            </p>
          </div>
        </section>

        <section
          id="fitting"
          ref={fittingRef}
          className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20"
        >
          <div className="mb-10 flex flex-col gap-2 text-center sm:text-left">
            <h2 className="font-display text-3xl font-semibold text-neutral-900 sm:text-4xl">
              피팅 시작하기
            </h2>
            <p className="text-neutral-600">
              왼쪽에 전신 사진, 가운데에 옷 이미지를 올린 뒤 결과 보기를 누르세요.
            </p>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1fr_1fr_minmax(200px,240px)] lg:items-stretch">
            <ImageDropzone
              label="내 사진 업로드"
              hint="JPG · PNG"
              guide="사람 사진은 정면 전신 사진이 가장 잘 나옵니다. 배경이 단순할수록 좋습니다."
              value={userFile}
              onFileChange={setUserFile}
            />
            <ImageDropzone
              label="옷 사진 업로드"
              hint="JPG · PNG"
              guide="단품 컷이나 모델 착용 컷 모두 사용할 수 있습니다. 옷이 잘 보이는 이미지를 권장합니다."
              value={clothFile}
              onFileChange={setClothFile}
            />
            <div className="flex flex-col justify-center gap-4 rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-neutral-600">
                두 이미지가 모두 준비되면 AI 가상 피팅을 실행합니다.
              </p>
              <button
                type="button"
                disabled={!canSubmit}
                onClick={handleTryOn}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-neutral-900 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    처리 중…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" aria-hidden />
                    결과 보기
                  </>
                )}
              </button>
              {!userFile || !clothFile ? (
                <p className="text-xs text-neutral-400">
                  전신 사진과 옷 사진을 모두 업로드하면 버튼이 활성화됩니다.
                </p>
              ) : null}
            </div>
          </div>

          {loading ? (
            <div
              className="mt-12 rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm"
              role="status"
              aria-live="polite"
            >
              <p className="text-center text-sm font-medium text-neutral-700">
                AI가 옷을 입혀드리는 중입니다…
              </p>
              <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-neutral-100">
                <div className="progress-indeterminate-bar h-full w-1/4 rounded-full bg-neutral-800" />
              </div>
              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="skeleton-shimmer aspect-[3/4] rounded-xl"
                  />
                ))}
              </div>
            </div>
          ) : null}

          {error ? (
            <div
              className="mt-8 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {error}
            </div>
          ) : null}

          {resultUrl && userPreviewUrl && clothPreviewUrl ? (
            <div className="mt-14 space-y-10 border-t border-neutral-200 pt-14">
              <div className="text-center sm:text-left">
                <h3 className="font-display text-2xl font-semibold text-neutral-900 sm:text-3xl">
                  피팅 결과
                </h3>
                <p className="mt-1 text-sm text-neutral-600">
                  원본과 옷, 결과를 한 화면에서 비교할 수 있습니다.
                </p>
              </div>

              <div className="grid gap-6 sm:grid-cols-3">
                <figure className="overflow-hidden rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
                  <figcaption className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    <Camera className="h-3.5 w-3.5" aria-hidden />
                    원본 · 나
                  </figcaption>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={userPreviewUrl}
                    alt="업로드한 전신 사진"
                    className="aspect-[3/4] w-full rounded-lg object-cover"
                  />
                </figure>
                <figure className="overflow-hidden rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
                  <figcaption className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    <Shirt className="h-3.5 w-3.5" aria-hidden />
                    옷
                  </figcaption>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={clothPreviewUrl}
                    alt="업로드한 옷 이미지"
                    className="aspect-[3/4] w-full rounded-lg object-cover"
                  />
                </figure>
                <figure className="overflow-hidden rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm">
                  <figcaption className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    <Sparkles className="h-3.5 w-3.5" aria-hidden />
                    가상 피팅
                  </figcaption>
                  <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-neutral-100">
                    <Image
                      src={resultUrl}
                      alt="가상 피팅 결과"
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, 33vw"
                      unoptimized
                    />
                  </div>
                </figure>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
                <p className="mb-4 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500 sm:text-left">
                  Before / After
                </p>
                <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
                  <div className="flex flex-1 flex-col gap-3">
                    <div className="flex justify-center gap-2 sm:justify-start">
                      <button
                        type="button"
                        onClick={() => setCompareMode("before")}
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                          compareMode === "before"
                            ? "bg-neutral-900 text-white"
                            : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                        }`}
                      >
                        내 원본
                      </button>
                      <button
                        type="button"
                        onClick={() => setCompareMode("after")}
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                          compareMode === "after"
                            ? "bg-neutral-900 text-white"
                            : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                        }`}
                      >
                        피팅 후
                      </button>
                    </div>
                    <div className="relative aspect-[3/4] max-h-[min(70vh,520px)] w-full overflow-hidden rounded-xl bg-neutral-100">
                      {largeSrc ? (
                        compareMode === "after" && resultUrl ? (
                          <Image
                            src={resultUrl}
                            alt={largeAlt}
                            fill
                            className="object-contain"
                            sizes="(max-width: 1024px) 100vw, 60vw"
                            unoptimized
                          />
                        ) : (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={largeSrc}
                            alt={largeAlt}
                            className="h-full w-full object-contain"
                          />
                        )
                      ) : null}
                    </div>
                  </div>
                  <div className="flex w-full flex-col items-center gap-3 lg:w-44">
                    <p className="text-xs font-medium text-neutral-500">
                      참고 · 옷
                    </p>
                    <div className="relative h-52 w-full overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 sm:h-64 lg:h-48 lg:w-full">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={clothPreviewUrl}
                        alt=""
                        className="h-full w-full object-contain"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-start">
                <button
                  type="button"
                  onClick={downloadResult}
                  className="inline-flex items-center gap-2 rounded-full border border-neutral-300 bg-white px-5 py-2.5 text-sm font-semibold text-neutral-900 transition hover:bg-neutral-50"
                >
                  <Download className="h-4 w-4" aria-hidden />
                  이미지 다운로드
                </button>
                <button
                  type="button"
                  onClick={shareResult}
                  className="inline-flex items-center gap-2 rounded-full border border-neutral-300 bg-white px-5 py-2.5 text-sm font-semibold text-neutral-900 transition hover:bg-neutral-50"
                >
                  <Share2 className="h-4 w-4" aria-hidden />
                  SNS에 공유하기
                </button>
                <button
                  type="button"
                  onClick={resetToUpload}
                  className="inline-flex items-center gap-2 rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden />
                  다시 시도하기
                </button>
              </div>
            </div>
          ) : null}
        </section>
      </main>

      <footer className="border-t border-neutral-200 bg-white py-8 text-center text-xs text-neutral-400">
        © {new Date().getFullYear()} AI Virtual Fitting Room
      </footer>
    </div>
  );
}
