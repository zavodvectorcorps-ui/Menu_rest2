import { useState, useCallback } from 'react';
import Cropper from 'react-easy-crop';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Loader2, Crop as CropIcon } from 'lucide-react';

const ASPECT_OPTIONS = [
  { label: '16:9', value: 16 / 9 },
  { label: '4:3', value: 4 / 3 },
  { label: '1:1', value: 1 },
  { label: '3:4', value: 3 / 4 },
  { label: 'Свободно', value: null },
];

// Returns a Blob of the cropped image
async function getCroppedBlob(imageSrc, pixelCrop) {
  const image = new Image();
  image.crossOrigin = 'anonymous';
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = reject;
    image.src = imageSrc;
  });

  const canvas = document.createElement('canvas');
  canvas.width = pixelCrop.width;
  canvas.height = pixelCrop.height;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(
    image,
    pixelCrop.x, pixelCrop.y, pixelCrop.width, pixelCrop.height,
    0, 0, pixelCrop.width, pixelCrop.height
  );

  return new Promise((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/jpeg', 0.92);
  });
}

export default function ImageCropDialog({ open, onOpenChange, imageSrc, onCropDone, busy }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [aspect, setAspect] = useState(16 / 9);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);

  const onCropComplete = useCallback((_area, areaPixels) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  const handleConfirm = async () => {
    if (!croppedAreaPixels) return;
    const blob = await getCroppedBlob(imageSrc, croppedAreaPixels);
    onCropDone(blob);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl" data-testid="image-crop-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-heading">
            <CropIcon className="w-5 h-5" />
            Кадрирование изображения
          </DialogTitle>
        </DialogHeader>

        <div className="relative w-full h-[55vh] bg-muted rounded-xl overflow-hidden">
          {imageSrc && (
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              aspect={aspect || undefined}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={onCropComplete}
              objectFit="contain"
              restrictPosition={false}
            />
          )}
        </div>

        <div className="space-y-4 py-3">
          <div>
            <Label className="text-sm mb-2 block">Соотношение сторон</Label>
            <div className="flex flex-wrap gap-2">
              {ASPECT_OPTIONS.map((o) => (
                <Button
                  key={o.label}
                  type="button"
                  size="sm"
                  variant={aspect === o.value ? 'default' : 'outline'}
                  className={aspect === o.value ? 'bg-mint-500 hover:bg-mint-600 rounded-full' : 'rounded-full'}
                  onClick={() => setAspect(o.value)}
                  data-testid={`crop-aspect-${o.label}`}
                >
                  {o.label}
                </Button>
              ))}
            </div>
          </div>

          <div>
            <Label className="text-sm mb-2 block">Масштаб: {zoom.toFixed(1)}×</Label>
            <Slider
              min={1}
              max={4}
              step={0.1}
              value={[zoom]}
              onValueChange={(v) => setZoom(v[0])}
              data-testid="crop-zoom-slider"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Отмена
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={busy || !croppedAreaPixels}
            className="bg-mint-500 hover:bg-mint-600 text-white gap-2"
            data-testid="crop-confirm-btn"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <CropIcon className="w-4 h-4" />}
            {busy ? 'Загрузка...' : 'Применить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
