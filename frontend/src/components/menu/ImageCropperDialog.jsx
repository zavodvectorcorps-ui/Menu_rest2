import { useState, useCallback, useEffect } from 'react';
import Cropper from 'react-easy-crop';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import { Slider } from '@/components/ui/slider';
import { toast } from 'sonner';

const ASPECT_PRESETS = [
  { label: '1:1', value: 1 },
  { label: '4:5', value: 4 / 5 },
  { label: '3:4', value: 3 / 4 },
  { label: '16:9', value: 16 / 9 },
  { label: 'Свободно', value: null },
];

/**
 * Crops the given source-area of an <img> to a Blob (JPEG, quality 0.92).
 * We first draw at the original resolution, then optionally down-scale
 * so the output never exceeds 2048px on the long side (keeps uploads sane).
 */
async function getCroppedBlob(imageSrc, pixelCrop) {
  const image = await new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = imageSrc;
  });

  const MAX_OUT = 2048;
  const longSide = Math.max(pixelCrop.width, pixelCrop.height);
  const scale = longSide > MAX_OUT ? MAX_OUT / longSide : 1;
  const outW = Math.round(pixelCrop.width * scale);
  const outH = Math.round(pixelCrop.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = outW;
  canvas.height = outH;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(
    image,
    pixelCrop.x, pixelCrop.y, pixelCrop.width, pixelCrop.height,
    0, 0, outW, outH
  );

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.92);
  });
}

/**
 * Modal that lets the user crop and zoom an image before upload.
 * Props:
 *   open, onOpenChange
 *   imageSrc (data URL) — раскодированный оригинал
 *   filename — имя исходного файла, будет использоваться при экспорте
 *   onCropped(blob, filename) — вызывается после «Сохранить»
 */
export function ImageCropperDialog({ open, onOpenChange, imageSrc, filename, onCropped }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [aspect, setAspect] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [saving, setSaving] = useState(false);

  // Reset all local state on dialog open, so each new image starts fresh
  // (previous zoom/rotation/aspect must not leak between uploads).
  useEffect(() => {
    if (open) {
      setCrop({ x: 0, y: 0 });
      setZoom(1);
      setRotation(0);
      setAspect(1);
      setCroppedAreaPixels(null);
    }
  }, [open]);

  const onCropComplete = useCallback((_area, areaPixels) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  const reset = () => {
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setRotation(0);
  };

  const handleSave = async () => {
    if (!croppedAreaPixels || !imageSrc) return;
    setSaving(true);
    try {
      const blob = await getCroppedBlob(imageSrc, croppedAreaPixels);
      if (!blob) {
        toast.error('Не удалось создать изображение (браузер отказал в canvas)');
        return;
      }
      // Preserve extension where possible — cropper always outputs JPEG.
      const base = (filename || 'image').replace(/\.[^.]+$/, '');
      onCropped(blob, `${base}.jpg`);
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl" data-testid="image-cropper-dialog">
        <DialogHeader>
          <DialogTitle>Кадрирование изображения</DialogTitle>
          <DialogDescription>
            Перетащите картинку и настройте масштаб. Выберите соотношение сторон для нужного места (карточка блюда — 1:1 или 4:5).
          </DialogDescription>
        </DialogHeader>

        <div className="relative w-full h-[420px] bg-black/60 rounded-lg overflow-hidden">
          {imageSrc && (
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              rotation={rotation}
              aspect={aspect}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onRotationChange={setRotation}
              onCropComplete={onCropComplete}
              showGrid
              restrictPosition
              minZoom={1}
              maxZoom={5}
              zoomSpeed={0.5}
            />
          )}
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-muted-foreground mr-1">Соотношение:</span>
            {ASPECT_PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setAspect(p.value)}
                className={
                  'text-xs px-2.5 py-1 rounded-full border transition-colors ' +
                  (aspect === p.value
                    ? 'bg-mint-500 text-white border-mint-500'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100')
                }
                data-testid={`cropper-aspect-${p.label}`}
              >
                {p.label}
              </button>
            ))}
            <button
              type="button"
              onClick={reset}
              className="ml-auto text-xs px-2.5 py-1 rounded-full border bg-white text-slate-600 border-slate-300 hover:bg-slate-100"
              data-testid="cropper-reset"
            >
              Сбросить
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-muted-foreground">Масштаб</span>
                <span className="text-xs text-muted-foreground tabular-nums">{zoom.toFixed(2)}×</span>
              </div>
              <Slider
                min={1}
                max={5}
                step={0.05}
                value={[zoom]}
                onValueChange={(v) => setZoom(v[0])}
                data-testid="cropper-zoom-slider"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-muted-foreground">Поворот</span>
                <span className="text-xs text-muted-foreground tabular-nums">{rotation}°</span>
              </div>
              <Slider
                min={-180}
                max={180}
                step={1}
                value={[rotation]}
                onValueChange={(v) => setRotation(v[0])}
                data-testid="cropper-rotation-slider"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button onClick={handleSave} disabled={saving || !croppedAreaPixels} data-testid="cropper-save-btn">
            {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Сохранение…</> : 'Сохранить и загрузить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
