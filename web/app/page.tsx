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

/** 합성 결과가 data URL일 때 fetch/공유가 브라우저마다 다를 수 있어 Blob으로 통일 */
async function resultUrlToBlob(resultUrl: string): Promise<Blob> {
  const res = await fetch(resultUrl);
  if (!res.ok) throw new Error("결과 이미지를 불러오지 못했습니다.");
  return res.blob();
}

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
      const blob = await resultUrlToBlob(resultUrl);
      const imageBitmap = await createImageBitmap(blob);
      const canvas = document.createElement("canvas");
      canvas.width = imageBitmap.width;
      canvas.height = imageBitmap.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("이미지 변환 컨텍스트를 만들 수 없습니다.");
      ctx.drawImage(imageBitmap, 0, 0);
      const pngBlob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((value) => {
          if (value) resolve(value);
          else reject(new Error("PNG 변환에 실패했습니다."));
        }, "image/png");
      });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(pngBlob);
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
      const blob = await resultUrlToBlob(resultUrl);
      const file = new File([blob], "virtual-fitting.png", { type: blob.type || "image/png" });
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
      const clipBlob = await resultUrlToBlob(resultUrl);
      if (navigator.clipboard?.write) {
        const mime = clipBlob.type || "image/png";
        await navigator.clipboard.write([new ClipboardItem({ [mime]: clipBlob })]);
        alert("결과 이미지가 클립보드에 복사되었습니다. 메신저 등에 붙여넣기 하세요.");
        return;
      }
    } catch {
      /* fall through */
    }
    try {
      if (!resultUrl.startsWith("data:")) {
        await navigator.clipboard.writeText(resultUrl);
        alert("결과 이미지 URL이 클립보드에 복사되었습니다.");
        return;
      }
    } catch {
      /* fall through */
    }
    alert("공유에 실패했습니다. 다운로드 후 직접 공유해 주세요.");
  };

  const largeSrc =
    compareMode === "before" ? userPreviewUrl : resultUrl || userPreviewUrl;
  const largeAlt =
    compareMode === "before" ? "원본 전신 사진" : "의상 교체 후 합성 이미지";

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
              내 사진은 그대로,
              <br />
              옷만 갈아입혀 보기
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-neutral-600">
              이 서비스는 <strong className="font-semibold text-neutral-800">배경 지우기·얼굴 합성 등은 하지 않습니다.</strong>{" "}
              <strong className="font-semibold text-neutral-800">내 전신 사진</strong>과{" "}
              <strong className="font-semibold text-neutral-800">옷 사진</strong>만 받아,{" "}
              내 사진 속 <strong className="font-semibold text-neutral-800">인물·포즈·배경은 유지</strong>한 채{" "}
              <strong className="font-semibold text-neutral-800">입고 있던 옷만</strong> 옷 사진의 옷으로 바꾼{" "}
              <strong className="font-semibold text-neutral-800">이미지 1장</strong>을 만듭니다.
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
              왼쪽은 <strong className="font-medium text-neutral-800">피팅될 나(전신)</strong>,
              가운데는 <strong className="font-medium text-neutral-800">입히고 싶은 옷</strong>
              (옷만 보이는 사진 또는 모델이 입은 사진)입니다. 결과는 항상{" "}
              <strong className="font-medium text-neutral-800">합성 이미지 1장</strong>입니다.
            </p>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1fr_1fr_minmax(200px,240px)] lg:items-stretch">
            <ImageDropzone
              label="내 사진 업로드"
              hint="JPG · PNG · WebP"
              guide="가상 피팅이 적용될 인물(나)입니다. 정면 전신이 가장 잘 나옵니다."
              value={userFile}
              onFileChange={setUserFile}
            />
            <ImageDropzone
              label="옷 사진 업로드"
              hint="JPG · PNG · WebP"
              guide="입히고 싶은 옷입니다. 옷만 찍은 상품 컷이나, 모델이 입고 있는 사진 모두 가능합니다. (모델 얼굴·몸은 결과에 쓰이지 않고 옷 참고용입니다.)"
              value={clothFile}
              onFileChange={setClothFile}
            />
            <div className="flex flex-col justify-center gap-4 rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-neutral-600">
                준비되면 내 전신 사진 위에, 옷 이미지의 의상만 합성한 1장을 받습니다.
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
                    옷 합성하기
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
                  의상 교체 결과
                </h3>
                <p className="mt-1 text-sm text-neutral-600">
                  아래 오른쪽이 <strong className="font-medium text-neutral-800">옷만 바뀐 최종 이미지 1장</strong>
                  입니다. 왼쪽·가운데는 입력으로 넣은 참고용입니다.
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
                    옷만 바뀐 결과
                  </figcaption>
                  <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-neutral-100">
                    <Image
                      src={resultUrl}
                      alt="의상만 교체된 합성 결과"
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
                  원본 vs 옷 교체 후
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
                        옷 교체 후
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
