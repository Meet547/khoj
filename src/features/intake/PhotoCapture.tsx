'use client';
import { useEffect, useState } from 'react';
import { Camera, X, LoaderCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { ErrorBox } from '@/components/ui/index';
async function compress(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.size > 15 * 1024 * 1024) throw new Error('invalid');
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement('canvas');
  const ratio = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  canvas.width = Math.round(bitmap.width * ratio);
  canvas.height = Math.round(bitmap.height * ratio);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('invalid');
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  let blob: Blob | null = null;
  for (const quality of [0.85, 0.7, 0.5, 0.3]) {
    blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, 'image/jpeg', quality));
    if (blob && blob.size < 1000000) break;
  }
  if (!blob || blob.size >= 1000000) throw new Error('invalid');
  return new File([blob], `khoj-photo-${crypto.randomUUID()}.jpg`, { type: 'image/jpeg' });
}
export function PhotoCapture({
  files,
  onChange,
  max = 1,
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max?: number;
}) {
  const t = useTranslations();
  const [previews, setPreviews] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const urls = files.map((x) => URL.createObjectURL(x));
    setPreviews(urls);
    return () => urls.forEach((x) => URL.revokeObjectURL(x));
  }, [files]);
  async function pick(selected: FileList | null) {
    if (!selected) return;
    setError('');
    setBusy(true);
    try {
      const next = await Promise.all(
        Array.from(selected)
          .slice(0, max - files.length)
          .map(compress),
      );
      onChange([...files, ...next]);
    } catch {
      setError(t('photoError'));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="photo-thumbs">
        {previews.map((url, i) => (
          <div className="photo-thumb" key={url}>
            <img src={url} alt={`${t('photo')} ${i + 1}`} />
            <button
              type="button"
              aria-label={`${t('removePhoto')} ${i + 1}`}
              onClick={() => onChange(files.filter((_, j) => j !== i))}
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
      {files.length < max && (
        <label className="photo-drop">
          {busy ? <LoaderCircle className="spinner" size={30} /> : <Camera size={32} />}
          <span>{t('addPhoto')}</span>
          <small>
            JPG, PNG, WEBP · {max === 1 ? '1' : `1–${max}`} {t('photo')}
          </small>
          <input
            className="sr-only"
            type="file"
            accept="image/*"
            capture="environment"
            multiple={max > 1}
            disabled={busy}
            onChange={(e) => {
              void pick(e.target.files);
              e.target.value = '';
            }}
          />
        </label>
      )}
      {error && <ErrorBox message={error} />}
    </>
  );
}
