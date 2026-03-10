import { useState, useEffect } from 'react';
import { Bot, Trash2, RefreshCw, Copy, Check, Loader2, Users, Unplug, Plug, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

export default function TelegramBotPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [botInfo, setBotInfo] = useState(null);
  const [webhookSet, setWebhookSet] = useState(false);
  const [subscribers, setSubscribers] = useState([]);
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchBotData = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/restaurants/${currentRestaurantId}/telegram-bot`, authHeaders);
      setBotToken(resp.data.bot_token || '');
      setBotInfo(resp.data.bot_info);
      setWebhookSet(resp.data.webhook_set);
      setSubscribers(resp.data.subscribers || []);
    } catch (err) {
      toast.error('Ошибка загрузки настроек бота');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBotData(); }, [currentRestaurantId]);

  const saveBotToken = async () => {
    if (!botToken.trim()) {
      toast.error('Введите токен бота');
      return;
    }
    setSaving(true);
    try {
      await axios.put(
        `${API}/restaurants/${currentRestaurantId}/telegram-bot`,
        { telegram_bot_token: botToken },
        authHeaders
      );
      toast.success('Бот подключён!');
      fetchBotData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка подключения бота');
    } finally {
      setSaving(false);
    }
  };

  const disconnectBot = async () => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/telegram-bot`, authHeaders);
      toast.success('Бот отключён');
      setBotToken('');
      setBotInfo(null);
      setWebhookSet(false);
      setSubscribers([]);
      setDisconnectOpen(false);
    } catch (err) {
      toast.error('Ошибка отключения бота');
    }
  };

  const removeSubscriber = async (chatId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/telegram-bot/subscribers/${chatId}`, authHeaders);
      setSubscribers(prev => prev.filter(s => s.chat_id !== chatId));
      toast.success('Подписчик удалён');
    } catch (err) {
      toast.error('Ошибка удаления');
    }
  };

  const copyBotLink = () => {
    if (botInfo?.username) {
      navigator.clipboard.writeText(`https://t.me/${botInfo.username}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success('Ссылка скопирована');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isConnected = botInfo && botToken;

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="telegram-bot-page">
      <div>
        <h1 className="text-2xl font-heading font-bold text-foreground">Telegram-бот</h1>
        <p className="text-muted-foreground">Уведомления о вызовах персонала и заказах</p>
      </div>

      {/* Bot Connection Card */}
      <Card className="border-none shadow-md">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isConnected ? 'bg-green-500/10' : 'bg-muted'}`}>
                <Bot className={`w-5 h-5 ${isConnected ? 'text-green-500' : 'text-muted-foreground'}`} />
              </div>
              <div>
                <CardTitle className="text-lg font-heading">
                  {isConnected ? botInfo.first_name : 'Подключение бота'}
                </CardTitle>
                <CardDescription>
                  {isConnected ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                      @{botInfo.username} — подключён
                    </span>
                  ) : 'Введите токен от @BotFather'}
                </CardDescription>
              </div>
            </div>
            {isConnected && (
              <Button variant="outline" size="sm" className="gap-1.5 text-destructive hover:text-destructive" onClick={() => setDisconnectOpen(true)} data-testid="disconnect-bot-btn">
                <Unplug className="w-4 h-4" />
                Отключить
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Токен бота</Label>
            <div className="flex gap-2">
              <Input
                type="password"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                className="font-mono text-sm"
                data-testid="bot-token-input"
              />
              <Button onClick={saveBotToken} disabled={saving} className="gap-2 bg-mint-500 hover:bg-mint-600 flex-shrink-0" data-testid="save-bot-token-btn">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
                {saving ? 'Подключение...' : 'Подключить'}
              </Button>
            </div>
          </div>

          {/* Instructions */}
          {!isConnected && (
            <div className="bg-muted/50 rounded-xl p-4 space-y-3">
              <h4 className="font-medium text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-blue-500" />
                Как создать бота
              </h4>
              <ol className="text-sm text-muted-foreground space-y-1.5 list-decimal list-inside">
                <li>Откройте <strong>@BotFather</strong> в Telegram</li>
                <li>Отправьте команду <code className="bg-background px-1 py-0.5 rounded">/newbot</code></li>
                <li>Задайте имя и username для бота</li>
                <li>Скопируйте токен и вставьте выше</li>
              </ol>
            </div>
          )}

          {/* Connected Info */}
          {isConnected && (
            <div className="bg-muted/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Ссылка на бота:</span>
                <Button variant="ghost" size="sm" className="gap-1.5 h-7" onClick={copyBotLink} data-testid="copy-bot-link">
                  {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                  https://t.me/{botInfo.username}
                </Button>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Webhook:</span>
                <Badge variant={webhookSet ? "default" : "destructive"} className={webhookSet ? "bg-green-500/10 text-green-600 border-green-200" : ""}>
                  {webhookSet ? 'Установлен' : 'Не установлен'}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Отправьте ссылку на бота персоналу. После нажатия /start они будут получать уведомления о вызовах и заказах.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Subscribers */}
      {isConnected && (
        <Card className="border-none shadow-md">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <CardTitle className="text-lg font-heading">Подписчики</CardTitle>
                  <CardDescription>Персонал, получающий уведомления</CardDescription>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={fetchBotData} data-testid="refresh-subscribers">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {subscribers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Пока нет подписчиков</p>
                <p className="text-xs mt-1">Отправьте ссылку на бота персоналу</p>
              </div>
            ) : (
              <div className="space-y-2">
                {subscribers.map((sub) => (
                  <div key={sub.chat_id} className="flex items-center justify-between p-3 rounded-xl bg-muted/50" data-testid={`subscriber-${sub.chat_id}`}>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-600">
                          {(sub.first_name || sub.username || '?')[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium">{sub.first_name || 'Без имени'}</p>
                        {sub.username && <p className="text-xs text-muted-foreground">@{sub.username}</p>}
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => removeSubscriber(sub.chat_id)} data-testid={`remove-subscriber-${sub.chat_id}`}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Disconnect Dialog */}
      <Dialog open={disconnectOpen} onOpenChange={setDisconnectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Отключить бота?</DialogTitle>
            <DialogDescription>
              Бот перестанет получать уведомления. Все подписчики будут удалены.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisconnectOpen(false)}>Отмена</Button>
            <Button variant="destructive" onClick={disconnectBot} data-testid="confirm-disconnect-btn">Отключить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
