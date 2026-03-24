"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { ImagePlus, Trash2, Upload } from "lucide-react";

const ALLOWED = new Set(["image/jpeg", "image/png"]);

export type ImageDropzoneProps = {
  label: string;
  hint?: string;
  guide?: string;
  value: File | null;
  onFileChange: (file: File | null) => void;
};

export function ImageDropzone({
  label,
  hint,
  guide,
  value,
  onFileChange,
}: ImageDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [rejectMsg, setRejectMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!value) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(value);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  const applyFile = useCallback(
    (file: File | null) => {
      setRejectMsg(null);
      if (!file) {
        onFileChange(null);
        return;
      }
      if (!ALLOWED.has(file.type)) {
        setRejectMsg("JPG 또는 PNG 파일만 업로드할 수 있습니다.");
        return;
      }
      onFileChange(file);
    },
    [onFileChange],
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    applyFile(f);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0] ?? null;
    applyFile(f);
  };

  const clear = () => {
    applyFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const openPicker = () => inputRef.current?.click();

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-500">
          {label}
        </span>
        {hint ? (
          <span className="text-xs text-neutral-400">{hint}</span>
        ) : null}
      </div>
      {guide ? (
        <p className="text-sm leading-relaxed text-neutral-500">{guide}</p>
      ) : null}

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPicker();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={openPicker}
        className={[
          "relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-white px-4 py-8 transition-colors",
          dragOver
            ? "border-neutral-900 bg-neutral-50"
            : "border-neutral-200 hover:border-neutral-400",
        ].join(" ")}
        aria-label={`${label} 업로드 영역`}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept="image/jpeg,image/png,.jpg,.jpeg,.png"
          className="sr-only"
          onChange={onInputChange}
        />

        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={preview}
            alt=""
            className="max-h-48 w-full max-w-[200px] rounded-lg object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-neutral-400">
            <ImagePlus className="h-10 w-10" strokeWidth={1.25} />
            <span className="text-sm text-neutral-500">
              드래그하여 놓거나 클릭하여 선택
            </span>
          </div>
        )}
      </div>

      {rejectMsg ? (
        <p className="text-sm text-red-600" role="alert">
          {rejectMsg}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            openPicker();
          }}
          className="inline-flex items-center gap-1.5 rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-800 transition hover:bg-neutral-50"
        >
          <Upload className="h-4 w-4" aria-hidden />
          다시 올리기
        </button>
        {value ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              clear();
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
            삭제
          </button>
        ) : null}
      </div>
    </div>
  );
}
