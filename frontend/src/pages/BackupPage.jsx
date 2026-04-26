import { useState, useEffect } from 'react';
import axios from 'axios';
import { Database, Image as ImageIcon, Download, Loader2, FileArchive, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function BackupPage() {
  const [info, setInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(true);
  const [dlDb, setDlDb] = useState(false);
  const [dlUploads, setDlUploads] = useState(false);

  const authHeaders = {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  };

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/admin/backup/info`, authHeaders);
        setInfo(r.data);
      } catch {
        toast.error('Ошибка загрузки информации');
      } finally {
        setLoadingInfo(false);
      }
    })();
    // eslint-disable-next-line
  }, []);

  const downloadBlob = async (url, filename, setLoading) => {
    setLoading(true);
    try {
      const resp = await axios.post(url, null, { ...authHeaders, responseType: 'blob' });
      const blob = new Blob([resp.data], { type: 'application/gzip' });
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
      toast.success('Бэкап скачан');
    } catch (e) {
      toast.error(e.response?.status === 403 ? 'Нет прав' : 'Ошибка создания бэкапа');
    } finally {
      setLoading(false);
    }
  };

  const ts = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, '').slice(0, 15);

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="backup-page">
      <div>
        <h1 className="text-2xl font-heading font-bold text-foreground">Резервные копии</h1>
        <p className="text-muted-foreground">Скачайте архивы базы данных и загруженных изображений</p>
      </div>

      {/* Info card */}
      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <FileArchive className="w-5 h-5 text-mint-500 mt-0.5" />
          <div>
            <h2 className="font-heading font-semibold text-foreground">Текущее состояние</h2>
            <p className="text-sm text-muted-foreground">Сводка по базе и хранилищу</p>
          </div>
        </div>

        {loadingInfo ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Загрузка...
          </div>
        ) : info ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Stat label="Документов в БД" value={info.total_documents} testid="stat-docs" />
            <Stat label="Коллекций" value={Object.keys(info.collections || {}).length} testid="stat-collections" />
            <Stat label="Файлов в uploads" value={info.uploads_count} testid="stat-uploads-count" />
            <Stat label="Размер uploads" value={`${info.uploads_size_mb} МБ`} testid="stat-uploads-size" />
          </div>
        ) : null}
      </div>

      {/* Database backup */}
      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-mint-100 dark:bg-mint-900/30 flex items-center justify-center flex-shrink-0">
              <Database className="w-5 h-5 text-mint-500" />
            </div>
            <div>
              <h3 className="font-heading font-semibold text-foreground">База данных (MongoDB)</h3>
              <p className="text-sm text-muted-foreground">
                BSON-дамп всех коллекций. Распаковывается через <code className="text-xs bg-muted px-1 rounded">mongorestore</code>.
              </p>
            </div>
          </div>
          <Button
            className="rounded-full bg-mint-500 hover:bg-mint-600 text-white gap-2"
            disabled={dlDb}
            onClick={() => downloadBlob(`${API}/admin/backup/database`, `db_backup_${ts()}.tar.gz`, setDlDb)}
            data-testid="download-db-backup-btn"
          >
            {dlDb ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {dlDb ? 'Создание...' : 'Скачать бэкап БД'}
          </Button>
        </div>
      </div>

      {/* Uploads backup */}
      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center flex-shrink-0">
              <ImageIcon className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h3 className="font-heading font-semibold text-foreground">Загруженные изображения</h3>
              <p className="text-sm text-muted-foreground">
                Архив папки <code className="text-xs bg-muted px-1 rounded">uploads/</code> (фото блюд, логотипы).
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            className="rounded-full gap-2 border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20"
            disabled={dlUploads}
            onClick={() => downloadBlob(`${API}/admin/backup/uploads`, `uploads_backup_${ts()}.tar.gz`, setDlUploads)}
            data-testid="download-uploads-backup-btn"
          >
            {dlUploads ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {dlUploads ? 'Создание...' : 'Скачать бэкап файлов'}
          </Button>
        </div>
      </div>

      {/* Restore tip */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-2xl p-4">
        <div className="flex gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-900 dark:text-amber-200 space-y-1">
            <p className="font-semibold">Как восстановить</p>
            <p><strong>БД:</strong> распакуйте архив, затем выполните <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">mongorestore --drop --db restaurant_app dump/</code></p>
            <p><strong>Файлы:</strong> распакуйте архив в папку <code className="bg-amber-100 dark:bg-amber-900/40 px-1 rounded">backend/</code> и перезапустите backend.</p>
            <p className="text-xs opacity-75">Рекомендуется хранить бэкапы на внешнем устройстве (не на этом же сервере).</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, testid }) {
  return (
    <div className="bg-muted/50 rounded-xl p-3" data-testid={testid}>
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-heading font-bold text-foreground">{value}</div>
    </div>
  );
}
