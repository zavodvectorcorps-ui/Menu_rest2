import { useState, useRef } from 'react';
import { Upload, X, Loader2, Sparkles, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';
import { ImageCropperDialog } from './ImageCropperDialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function ImageUpload({ value, onChange, restaurantId }) {
  const [uploading, setUploading] = useState(false);
  const [cropSrc, setCropSrc] = useState(null);
  const [cropOpen, setCropOpen] = useState(false);
  const [origName, setOrigName] = useState('image');
  const [videoDialogOpen, setVideoDialogOpen] = useState(false);
  const [videoPrompt, setVideoPrompt] = useState('');
  const [videoDuration, setVideoDuration] = useState('5');
  const [videoJob, setVideoJob] = useState(null); // { request_id, status }
  const fileInputRef = useRef(null);

  const isCurrentVideo = /\.(mp4|webm|mov)(\?|$)/i.test(value || '');

  const getAuthHeaders = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  });

  // Start image-to-video generation
  const startVideoGeneration = async () => {
    if (!value || !restaurantId) {
      toast.error('Сначала загрузите фото');
      return;
    }
    // Отправляем абсолютный URL. fal.ai должен скачать картинку с публичного домена.
    let imgPath = value;
    if (imgPath.startsWith('/')) {
      // относительный путь — префиксуем текущим origin браузера
      imgPath = window.location.origin + imgPath;
    }
    if (!imgPath || !/^https?:\/\//i.test(imgPath)) {
      toast.error('Некорректный URL изображения');
      return;
    }
    setVideoJob({ status: 'submitting' });
    try {
      const resp = await axios.post(
        `${API}/restaurants/${restaurantId}/videos/generate`,
        { image_url: imgPath, prompt: videoPrompt, duration: videoDuration },
        getAuthHeaders()
      );
      const requestId = resp.data.request_id;
      setVideoJob({ request_id: requestId, status: 'queued' });
      toast.info('Задача отправлена. Обычно 30–90 секунд…');
      pollVideoStatus(requestId);
    } catch (e) {
      setVideoJob(null);
      toast.error(e.response?.data?.detail || 'Ошибка запуска генерации');
    }
  };

  const pollVideoStatus = async (requestId) => {
    let attempts = 0;
    const maxAttempts = 60; // ~ 5 минут при интервале 5 сек
    const interval = 5000;

    const tick = async () => {
      attempts++;
      try {
        const resp = await axios.get(
          `${API}/restaurants/${restaurantId}/videos/status/${requestId}`,
          getAuthHeaders()
        );
        const data = resp.data;
        setVideoJob({ request_id: requestId, status: data.status });

        if (data.status === 'completed' && data.video_url) {
          const fullUrl = `${BACKEND_URL}${data.video_url}`;
          onChange(fullUrl);
          setVideoJob(null);
          setVideoDialogOpen(false);
          toast.success('Видео готово!');
          return;
        }
        if (data.status === 'failed') {
          setVideoJob(null);
          toast.error(`Ошибка генерации: ${data.error || 'неизвестно'}`);
          return;
        }
        if (attempts < maxAttempts) {
          setTimeout(tick, interval);
        } else {
          setVideoJob(null);
          toast.error('Слишком долго. Попробуйте позже.');
        }
      } catch (e) {
        setVideoJob(null);
        toast.error(e.response?.data?.detail || 'Ошибка проверки статуса');
      }
    };
    setTimeout(tick, interval);
  };

  // Read the file. Image → open cropper; video → upload directly.
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    // reset the input so re-selecting the same file re-triggers onChange
    if (e.target) e.target.value = '';
    if (!file) return;

    const isVideo = file.type.startsWith('video/');
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const videoTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
    const allowedTypes = [...imageTypes, ...videoTypes];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Формат: JPG, PNG, GIF, WebP, MP4, WebM, MOV');
      return;
    }
    const limit = isVideo ? 30 * 1024 * 1024 : 15 * 1024 * 1024;
    if (file.size > limit) {
      toast.error(`Файл слишком большой. Максимум ${isVideo ? '30MB (видео)' : '15MB (фото)'}`);
      return;
    }

    // Video → upload directly, no cropping.
    if (isVideo) {
      uploadFileDirect(file);
      return;
    }

    // Image → run through cropper.
    const reader = new FileReader();
    reader.onload = () => {
      setCropSrc(reader.result);
      setOrigName(file.name || 'image');
      setCropOpen(true);
    };
    reader.onerror = () => toast.error('Не удалось прочитать файл');
    reader.readAsDataURL(file);
  };

  const uploadFileDirect = async (fileObj) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', fileObj, fileObj.name);
      const response = await axios.post(`${API}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const url = `${BACKEND_URL}${response.data.url}`;
      onChange(url);
      toast.success(response.data.is_video ? 'Видео загружено' : 'Изображение загружено');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  // Called by ImageCropperDialog once the user confirms.
  const uploadCroppedBlob = async (blob, filename) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', blob, filename || 'image.jpg');
      const response = await axios.post(`${API}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const imageUrl = `${BACKEND_URL}${response.data.url}`;
      onChange(imageUrl);
      toast.success('Изображение загружено');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-2">
      <Label>Изображение</Label>
      
      {value ? (
        <div className="relative">
          {/\.(mp4|webm|mov)(\?|$)/i.test(value) ? (
            <video
              src={value}
              className="w-full h-40 object-cover rounded-lg border border-border bg-black"
              autoPlay muted loop playsInline
              preload="metadata"
            />
          ) : (
            <img
              src={value}
              alt="Preview"
              className="w-full h-40 object-cover rounded-lg border border-border"
            />
          )}
          <Button
            variant="destructive"
            size="icon"
            className="absolute top-2 right-2 h-8 w-8 rounded-full"
            onClick={() => onChange('')}
          >
            <X className="w-4 h-4" />
          </Button>
          {!isCurrentVideo && restaurantId && (
            <Button
              size="sm"
              className="absolute bottom-2 left-2 h-8 rounded-full gap-1.5 bg-purple-600 hover:bg-purple-700 text-white shadow-md"
              onClick={() => { setVideoPrompt(''); setVideoDialogOpen(true); }}
              disabled={!!videoJob}
              data-testid="animate-photo-btn"
            >
              <Wand2 className="w-3.5 h-3.5" />
              {videoJob ? `${videoJob.status}…` : 'Оживить (AI)'}
            </Button>
          )}
        </div>
      ) : (
        <div 
          className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-mint-500 hover:bg-mint-50/50 dark:hover:bg-mint-900/10 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-mint-500 animate-spin" />
              <p className="text-sm text-muted-foreground">Загрузка...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Нажмите для загрузки изображения или видео
              </p>
              <p className="text-xs text-muted-foreground">
                Фото до 15MB · Видео (MP4/WebM/MOV) до 30MB
              </p>
            </div>
          )}
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp,video/mp4,video/webm,video/quicktime"
        className="hidden"
        onChange={handleFileSelect}
        disabled={uploading}
      />
      
      <div className="flex items-center gap-2">
        <Input
          placeholder="Или введите URL изображения"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="text-sm"
        />
      </div>

      <ImageCropperDialog
        open={cropOpen}
        onOpenChange={(v) => {
          setCropOpen(v);
          if (!v) setCropSrc(null); // release base64 memory when closed
        }}
        imageSrc={cropSrc}
        filename={origName}
        onCropped={uploadCroppedBlob}
      />

      <Dialog open={videoDialogOpen} onOpenChange={(v) => !videoJob && setVideoDialogOpen(v)}>
        <DialogContent className="max-w-lg" data-testid="animate-photo-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              Оживить фото (AI видео)
            </DialogTitle>
            <DialogDescription>
              fal.ai Kling 2.5 создаст короткое видео на основе загруженного фото. Опишите желаемое движение камеры или анимацию.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div>
              <Label className="text-xs">Промт (на английском работает лучше)</Label>
              <Textarea
                value={videoPrompt}
                onChange={(e) => setVideoPrompt(e.target.value)}
                placeholder="smooth camera rotation around the cocktail, light steam rising, cinematic lighting"
                rows={3}
                disabled={!!videoJob}
                data-testid="animate-prompt-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-xs">Длительность:</Label>
              {['5', '10'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setVideoDuration(d)}
                  disabled={!!videoJob}
                  className={
                    'text-xs px-3 py-1 rounded-full border transition-colors ' +
                    (videoDuration === d
                      ? 'bg-purple-600 text-white border-purple-600'
                      : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100')
                  }
                  data-testid={`animate-duration-${d}`}
                >
                  {d} сек
                </button>
              ))}
            </div>
            {videoJob && (
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Статус: <b>{videoJob.status}</b>. Обычно занимает 30–90 секунд.
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setVideoDialogOpen(false)} disabled={!!videoJob}>
              Отмена
            </Button>
            <Button
              onClick={startVideoGeneration}
              disabled={!!videoJob}
              className="bg-purple-600 hover:bg-purple-700 text-white"
              data-testid="animate-start-btn"
            >
              {videoJob ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Генерирую…</> : 'Создать видео'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
