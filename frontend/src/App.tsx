import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent, PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  useVoiceAssistant,
  useChat,
  useTranscriptions,
} from '@livekit/components-react';
import {
  Copy,
  Sparkles,
  Train,
  Plane,
  Film,
  Building2,
  ShoppingBag,
  Terminal,
  ExternalLink,
  Plus,
  Images,
  ImagePlus,
  MessageSquare,
  Send,
  Mic,
  Sun,
  Moon,
  Trash2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  GripVertical,
  Pencil,
  ArrowLeft,
  X,
  LogOut,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '@livekit/components-styles';
import './Assistant.css';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");

const playgroundCommands = [
  {
    title: 'World News Briefing',
    category: 'Intelligence',
    prompt: 'Give me the latest world news in two bullet points.',
  },
  {
    title: 'Open World Monitor',
    category: 'Visual Ops',
    prompt: 'Open the world monitor so I can see what is happening.',
  },
  {
    title: 'Live Web Search',
    category: 'Research',
    prompt: 'Search the web for the latest artificial intelligence breakthroughs today.',
  },
  {
    title: 'Search Trains',
    category: 'Bookings',
    prompt: 'Search available train routes from Mumbai to Delhi.',
  },
  {
    title: 'Book Train Ticket',
    category: 'Bookings',
    prompt: 'Book a 1A ticket on Mumbai Rajdhani 12951 for Tony Stark.',
  },
  {
    title: 'Search Flights',
    category: 'Bookings',
    prompt: 'Find scheduled flights from Mumbai to Delhi.',
  },
  {
    title: 'Book Flight',
    category: 'Bookings',
    prompt: 'Book flight AI-806 for Tony Stark in Business class.',
  },
  {
    title: 'Search Movies',
    category: 'Entertainment',
    prompt: 'What movies and showtimes are playing in Mumbai right now?',
  },
  {
    title: 'Book Movie Tickets',
    category: 'Entertainment',
    prompt: 'Book 2 tickets for Avengers Secret Wars at PVR ICON Palladium at 20:00.',
  },
  {
    title: 'Search Luxury Hotels',
    category: 'Hospitality',
    prompt: 'Search available luxury hotels and suites in Mumbai.',
  },
  {
    title: 'Book Hotel Stay',
    category: 'Hospitality',
    prompt: 'Reserve a Luxury Grand Room at The Taj Mahal Palace for Tony Stark for 2 nights.',
  },
  {
    title: 'List All Bookings',
    category: 'Operations',
    prompt: 'List all my active bookings and confirmed orders.',
  },
  {
    title: 'Store Memory',
    category: 'Memory',
    prompt: 'Remember that my favorite suit is the Mark 85 and my workshop passkey is 42.',
  },
  {
    title: 'Recall Memory',
    category: 'Memory',
    prompt: 'What do you recall about my suit preferences and workshop passkey?',
  },
  {
    title: 'Create Task',
    category: 'Operations',
    prompt: 'Create a high priority task to review arc reactor power efficiency.',
  },
  {
    title: 'List Tasks',
    category: 'Operations',
    prompt: 'List all my pending tasks and their priorities.',
  },
  {
    title: 'Diagnostic Audit',
    category: 'System',
    prompt: 'Run a full system diagnostic audit on all your subsystems.',
  },
];

interface BookingOrder {
  order_id: string;
  booking_type: string;
  title: string;
  description: string;
  amount: number;
  currency: string;
  status: string;
  payment_status: string;
  payment_session_id?: string;
  created_at: string;
  metadata?: Record<string, string | number | undefined>;
}

interface HealthStatus {
  status: string;
  uptime_seconds?: number;
  services?: Record<string, { status: string; message?: string }>;
}

type AssistantTheme = 'night' | 'day';
type MessageRole = 'user' | 'assistant';
type AuthChannel = 'email';
type AuthMode = 'signup' | 'signin';

interface AuthUser {
  id: string;
  email?: string;
  phone?: string;
  name?: string;
  avatar_url?: string;
}

interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: AuthUser;
}

interface ConversationMessage {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: string;
  photoIds?: string[];
  feedback?: 'positive' | 'negative';
}

interface MediaAsset {
  id: string;
  ownerId: string;
  conversationId: string;
  messageId: string;
  name: string;
  mimeType: string;
  createdAt: string;
  blob: Blob;
}

interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  messages: ConversationMessage[];
}

const CONVERSATIONS_STORAGE_KEY = 'friday-conversations-v1';
const THEME_STORAGE_KEY = 'friday-theme';
const AUTH_STORAGE_KEY = 'friday-auth-session-v1';
const MEDIA_DATABASE_NAME = 'friday-media-v1';

function normalizeAssistantMarkdown(text: string): string {
  const unescaped = text.replace(/\\([*_])/g, '$1');
  return unescaped.split('\n').map((line) => {
    const boldMarkers = line.match(/\*\*/g)?.length ?? 0;
    return boldMarkers % 2 === 0 ? line : line.replace(/\*\*/g, '');
  }).join('\n');
}

function openMediaDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(MEDIA_DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains('photos')) {
        database.createObjectStore('photos', { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('Unable to open the photo library.'));
  });
}

async function saveMediaAsset(asset: MediaAsset): Promise<void> {
  const database = await openMediaDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction('photos', 'readwrite');
    transaction.objectStore('photos').put(asset);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error('Unable to save the uploaded photo.'));
    transaction.onabort = () => reject(transaction.error ?? new Error('Saving the uploaded photo was interrupted.'));
  }).finally(() => database.close());
}

async function getMediaAsset(id: string): Promise<MediaAsset | undefined> {
  const database = await openMediaDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction('photos', 'readonly');
    const request = transaction.objectStore('photos').get(id) as IDBRequest<MediaAsset | undefined>;
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('Unable to load the uploaded photo.'));
    transaction.oncomplete = () => database.close();
    transaction.onerror = () => database.close();
    transaction.onabort = () => database.close();
  });
}

async function deleteMediaAsset(id: string): Promise<void> {
  const database = await openMediaDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction('photos', 'readwrite');
    transaction.objectStore('photos').delete(id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error('Unable to delete the photo.'));
    transaction.onabort = () => reject(transaction.error ?? new Error('Deleting the photo was interrupted.'));
  }).finally(() => database.close());
}

async function getMediaAssets(ownerId: string): Promise<MediaAsset[]> {
  const database = await openMediaDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction('photos', 'readonly');
    const request = transaction.objectStore('photos').getAll() as IDBRequest<MediaAsset[]>;
    request.onsuccess = () => resolve(
      request.result
        .filter((asset) => asset.ownerId === ownerId)
        .sort((left, right) => right.createdAt.localeCompare(left.createdAt)),
    );
    request.onerror = () => reject(request.error ?? new Error('Unable to load your photo library.'));
    transaction.oncomplete = () => database.close();
    transaction.onerror = () => database.close();
    transaction.onabort = () => database.close();
  });
}

let supabaseAuthClient: SupabaseClient | null = null;

async function getSupabaseAuthClient(): Promise<SupabaseClient> {
  if (supabaseAuthClient) return supabaseAuthClient;
  const response = await fetch(`${API_BASE_URL}/api/config`);
  const config: {
    supabase_url?: string | null;
    supabase_anon_key?: string | null;
  } = await response.json();
  if (!response.ok) throw new Error('Unable to load Google sign-in configuration.');
  if (!config.supabase_url || !config.supabase_anon_key) {
    throw new Error('Google sign-in is not configured. Add a Supabase publishable/anon key to the server environment.');
  }
  supabaseAuthClient = createClient(config.supabase_url, config.supabase_anon_key, {
    auth: { flowType: 'pkce' },
  });
  return supabaseAuthClient;
}

function conversationStorageKey(userId?: string) {
  return userId ? `${CONVERSATIONS_STORAGE_KEY}:${userId}` : CONVERSATIONS_STORAGE_KEY;
}

function loadConversations(userId?: string): Conversation[] {
  try {
    const saved = localStorage.getItem(conversationStorageKey(userId));
    if (!saved) return [];
    const parsed: unknown = JSON.parse(saved);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is Conversation =>
      typeof item?.id === 'string' &&
      typeof item?.title === 'string' &&
      Array.isArray(item?.messages),
    );
  } catch (error) {
    console.error('Unable to load saved conversations', error);
    return [];
  }
}

function loadAuthSession(): AuthSession | null {
  try {
    const saved = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!saved) return null;
    const parsed: unknown = JSON.parse(saved);
    if (
      typeof parsed !== 'object' || parsed === null ||
      !('access_token' in parsed) || typeof parsed.access_token !== 'string' ||
      !('refresh_token' in parsed) || typeof parsed.refresh_token !== 'string' ||
      !('expires_at' in parsed) || typeof parsed.expires_at !== 'number' ||
      !('user' in parsed) || typeof parsed.user !== 'object' || parsed.user === null ||
      !('id' in parsed.user) || typeof parsed.user.id !== 'string'
    ) return null;
    return parsed as AuthSession;
  } catch (error) {
    console.error('Unable to load authentication session', error);
    return null;
  }
}

function toAuthSession(data: {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  expires_at?: number;
  user?: AuthUser;
}): AuthSession {
  if (!data.access_token || !data.refresh_token || !data.user?.id) {
    throw new Error('The authentication service returned an incomplete session.');
  }
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: data.expires_at ?? Math.floor(Date.now() / 1000) + (data.expires_in ?? 3600),
    user: data.user,
  };
}

function getProfileAvatarUrl(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

async function getSavedConversations(session: AuthSession): Promise<Conversation[]> {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  const data: { error?: string; conversations?: Array<{
    id: string;
    title: string;
    updated_at: string;
    messages: ConversationMessage[];
  }> } = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to load saved conversations.');
  if (!Array.isArray(data.conversations)) {
    throw new Error('The conversation service returned an invalid response.');
  }
  return data.conversations.map((conversation) => ({
    id: conversation.id,
    title: conversation.title,
    updatedAt: conversation.updated_at,
    messages: conversation.messages,
  }));
}

async function putSavedConversation(session: AuthSession, conversation: Conversation) {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversation.id)}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        id: conversation.id,
        title: conversation.title,
        updated_at: conversation.updatedAt,
        messages: conversation.messages,
      }),
    },
  );
  const data: { error?: string } = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to save conversations.');
}

async function deleteSavedConversation(session: AuthSession, conversationId: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${session.access_token}` },
    },
  );
  const data: { error?: string } = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to delete the saved conversation.');
}

function storedTheme(): AssistantTheme {
  return localStorage.getItem(THEME_STORAGE_KEY) === 'day' ? 'day' : 'night';
}

function AuthPage({
  theme,
  mode,
  forced,
  onModeChange,
  onBack,
  onAuthenticated,
  onGoogleSignIn,
  googleError,
}: {
  theme: AssistantTheme;
  mode: AuthMode;
  forced: boolean;
  onModeChange: (mode: AuthMode) => void;
  onBack: () => void;
  onAuthenticated: (session: AuthSession, mode: AuthMode) => void;
  onGoogleSignIn: () => Promise<void>;
  googleError: string | null;
}) {
  const channel: AuthChannel = 'email';
  const [identifier, setIdentifier] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (googleError) setError(googleError);
  }, [googleError]);

  const startGoogleSignIn = async () => {
    setWorking(true);
    setError(null);
    try {
      await onGoogleSignIn();
    } catch (signInError) {
      setError(signInError instanceof Error ? signInError.message : 'Unable to start Google sign-in.');
    } finally {
      setWorking(false);
    }
  };

  const submitIdentifier = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, identifier, mode }),
      });
      const data: { error?: string; message?: string } = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to send verification code.');
      setCodeSent(true);
      setNotice(data.message || `We sent a 6-digit code to your ${channel}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to send verification code.');
    } finally {
      setWorking(false);
    }
  };

  const submitCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, identifier, code, mode }),
      });
      const data: {
        error?: string;
        access_token?: string;
        refresh_token?: string;
        expires_in?: number;
        expires_at?: number;
        user?: AuthUser;
      } = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to verify the code.');
      onAuthenticated(toAuthSession(data), mode);
    } catch (verificationError) {
      setError(verificationError instanceof Error ? verificationError.message : 'Unable to verify the code.');
    } finally {
      setWorking(false);
    }
  };

  const changeMode = (nextMode: AuthMode) => {
    setCodeSent(false);
    setCode('');
    setError(null);
    setNotice(null);
    onModeChange(nextMode);
  };

  return (
    <main className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <img
            src={theme === 'day' ? '/images/friday-logo-gradient.png' : '/images/friday-logo-neon.png'}
            alt="FRIDAY AI Assistant"
          />
        </div>
        <span className="auth-eyebrow">{mode === 'signup' ? 'CREATE YOUR ACCOUNT' : 'WELCOME BACK'}</span>
        <h1>{mode === 'signup' ? 'Unlock your FRIDAY workspace' : 'Sign in to FRIDAY'}</h1>
        <p className="auth-description">
          {forced
            ? 'You have used your two free conversations. Create an account or sign in to keep chatting without limits.'
              : 'Sign in or create an account to unlock unlimited conversations and keep your history on this browser.'}
        </p>

        <div className="auth-mode-switch" role="tablist" aria-label="Account access">
          <button type="button" role="tab" aria-selected={mode === 'signup'} onClick={() => changeMode('signup')}>
            Sign up
          </button>
          <button type="button" role="tab" aria-selected={mode === 'signin'} onClick={() => changeMode('signin')}>
            Sign in
          </button>
        </div>

        <button
          className="auth-google-button"
          type="button"
          onClick={() => void startGoogleSignIn()}
          disabled={working}
        >
          <span className="auth-google-mark" aria-hidden="true">G</span>
          {working ? 'Opening Google…' : 'Continue with Google'}
        </button>
        <div className="auth-divider"><span>or continue with email</span></div>

        {!codeSent ? (
          <form className="auth-form" onSubmit={submitIdentifier}>
            <label htmlFor="auth-identifier">Email address</label>
            <input
              id="auth-identifier"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder="you@example.com"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
            />
            <p className="auth-field-hint">
              We will send a one-time sign-in code to this address.
            </p>
            <button className="auth-submit" type="submit" disabled={working}>
              {working ? 'Sending code…' : 'Send verification code'}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={submitCode}>
            <label htmlFor="auth-code">6-digit verification code</label>
            <input
              id="auth-code"
              className="otp-input"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              placeholder="••••••"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              required
            />
            <p className="auth-field-hint">
              Sent to {identifier}.{' '}
              <button type="button" className="auth-inline-button" onClick={() => { setCodeSent(false); setCode(''); }}>
                Change
              </button>
            </p>
            <button className="auth-submit" type="submit" disabled={working || code.length !== 6}>
              {working ? 'Verifying…' : mode === 'signup' ? 'Verify and create account' : 'Verify and sign in'}
            </button>
            {notice && <p className="auth-notice" role="status">{notice}</p>}
          </form>
        )}

        {error && <p className="auth-error" role="alert">{error}</p>}
        <p className="auth-security-note">
          Your verification code is processed securely and is never stored in conversation history.
        </p>
        {forced ? (
          <button className="auth-back-button" type="button" onClick={onBack}>
            <ArrowLeft size={15} /> Back to your conversations
          </button>
        ) : (
          <p className="auth-back-link">
            {mode === 'signup' ? 'Already have an account?' : 'New to FRIDAY?'}{' '}
            <button type="button" className="auth-inline-button" onClick={() => changeMode(mode === 'signup' ? 'signin' : 'signup')}>
              {mode === 'signup' ? 'Sign in' : 'Create an account'}
            </button>
          </p>
        )}
      </div>
    </main>
  );
}

function createConversation(): Conversation {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: 'New conversation',
    updatedAt: now,
    messages: [],
  };
}

async function preparePhotoForUpload(file: File): Promise<File> {
  const image = await createImageBitmap(file);
  try {
    const scale = Math.min(1, 1600 / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Unable to prepare the photo for upload.');
    context.fillStyle = '#fff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
    if (!blob) throw new Error('Unable to prepare the photo for upload.');
    if (blob.size > 8 * 1024 * 1024) throw new Error('This photo is still too large to send.');
    const name = file.name.replace(/\.[^.]+$/, '') || 'photo';
    return new File([blob], `${name}.jpg`, { type: 'image/jpeg' });
  } finally {
    image.close();
  }
}

function PhotoThumbnail({
  photoId,
  alt,
  className,
}: {
  photoId: string;
  alt: string;
  className: string;
}) {
  const [image, setImage] = useState<{
    photoId: string;
    source: string | null;
    unavailable: boolean;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    void getMediaAsset(photoId).then((asset) => {
      if (!asset) throw new Error(`Saved photo ${photoId} is unavailable.`);
      objectUrl = URL.createObjectURL(asset.blob);
      if (!cancelled) setImage({ photoId, source: objectUrl, unavailable: false });
    }).catch((loadError: unknown) => {
      if (!cancelled) {
        console.error('Unable to load saved chat photo', loadError);
        setImage({ photoId, source: null, unavailable: true });
      }
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photoId]);

  const currentImage = image?.photoId === photoId ? image : null;
  return currentImage?.source
    ? <img className={className} src={currentImage.source} alt={alt} />
    : (
      <span className={`${className} photo-placeholder`} role="status">
        {currentImage?.unavailable ? 'Photo unavailable' : 'Loading photo…'}
      </span>
    );
}

function ConnectedWorkspace({
  identity,
  activeConversationId,
  onMessage,
  children,
}: {
  identity: string;
  activeConversationId: string | null;
  onMessage: (id: string, role: MessageRole, text: string, timestamp: number, attachments?: File[]) => Promise<void>;
  children: (state: string, sendMessage: (text: string, attachments?: File[]) => Promise<void>) => ReactNode;
}) {
  const { state } = useVoiceAssistant();
  const { chatMessages, send } = useChat();
  const transcriptions = useTranscriptions();
  const seenChatMessages = useRef(new Set<string>());
  const seenTranscriptions = useRef(new Map<string, string>());

  useEffect(() => {
    for (const message of chatMessages) {
      if (seenChatMessages.current.has(message.id)) continue;
      seenChatMessages.current.add(message.id);
      void onMessage(
        activeConversationId ?? '',
        message.from?.identity === identity ? 'user' : 'assistant',
        message.message,
        message.timestamp,
        message.attachedFiles,
      ).catch((error: unknown) => console.error('Unable to save chat message', error));
    }
  }, [activeConversationId, chatMessages, identity, onMessage]);

  useEffect(() => {
    for (const transcription of transcriptions) {
      const { id, timestamp } = transcription.streamInfo;
      if (seenTranscriptions.current.get(id) === transcription.text) continue;
      seenTranscriptions.current.set(id, transcription.text);
      void onMessage(
        activeConversationId ?? '',
        transcription.participantInfo.identity === identity ? 'user' : 'assistant',
        transcription.text,
        timestamp,
      ).catch((error: unknown) => console.error('Unable to save transcription', error));
    }
  }, [activeConversationId, identity, onMessage, transcriptions]);

  const sendMessage = useCallback(async (text: string, attachments?: File[]) => {
    const sentMessage = await send(text, attachments?.length ? { attachments } : undefined);
    await onMessage(
      activeConversationId ?? '',
      'user',
      sentMessage.message,
      sentMessage.timestamp,
      sentMessage.attachedFiles,
    );
  }, [activeConversationId, onMessage, send]);

  return <>{children(state, sendMessage)}</>;
}

export function PlaygroundSidebar({
  roomName,
  identity,
  health,
}: {
  roomName: string;
  identity: string;
  health: HealthStatus | null;
}) {
  const [copied, setCopied] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'commands' | 'orders'>('commands');
  const [orders, setOrders] = useState<BookingOrder[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);

  const fetchOrders = async () => {
    setLoadingOrders(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/bookings`);
      if (res.ok) {
        const data = await res.json();
        setOrders(data.orders || []);
      }
    } catch {
      // Graceful fallback
    } finally {
      setLoadingOrders(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 6000);
    return () => clearInterval(interval);
  }, []);

  const copyPrompt = async (prompt: string) => {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(prompt);
      setCopied(prompt);
      window.setTimeout(() => setCopied(null), 1200);
    }
  };

  const getBookingIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'train':
        return <Train size={18} color="#00F0FF" />;
      case 'flight':
        return <Plane size={18} color="#00F0FF" />;
      case 'movie':
        return <Film size={18} color="#00F0FF" />;
      case 'hotel':
        return <Building2 size={18} color="#00F0FF" />;
      default:
        return <ShoppingBag size={18} color="#00F0FF" />;
    }
  };

  return (
    <aside className="playground-panel">
      <div className="panel-header">
        <div>
          <Sparkles size={22} color="#00F0FF" />
        </div>
        <div>
          <p className="panel-label">Stark Industries AI Lab</p>
          <h2>FRIDAY Command Lab</h2>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '0.3rem', borderRadius: '10px' }}>
        <button
          type="button"
          onClick={() => setActiveTab('commands')}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: activeTab === 'commands' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
            border: activeTab === 'commands' ? '1px solid #00F0FF' : 'none',
            color: activeTab === 'commands' ? '#00F0FF' : 'rgba(255,255,255,0.6)',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem',
          }}
        >
          <Terminal size={14} />
          Directives
        </button>
        <button
          type="button"
          onClick={() => { setActiveTab('orders'); fetchOrders(); }}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: activeTab === 'orders' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
            border: activeTab === 'orders' ? '1px solid #00F0FF' : 'none',
            color: activeTab === 'orders' ? '#00F0FF' : 'rgba(255,255,255,0.6)',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem',
          }}
        >
          <ShoppingBag size={14} />
          Orders ({orders.length})
        </button>
      </div>

      <div className="panel-section">
        <h3>Active Session</h3>
        <p>
          Room: <strong>{roomName}</strong> &nbsp;|&nbsp; User: <strong>{identity}</strong>
        </p>
        <p className="note-box">
          Speak naturally into your microphone or trigger spoken directives below. FRIDAY detects your language automatically.
        </p>
      </div>

      {health?.services && (
        <div className="panel-section">
          <h3>Subsystem Health</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
            {Object.entries(health.services).map(([name, data]) => (
              <div
                key={name}
                style={{
                  padding: '0.4rem 0.6rem',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(0, 240, 255, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: data.status === 'healthy' ? '#00F0FF' : '#FFB400',
                  }}
                />
                <span style={{ textTransform: 'capitalize' }}>{name.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'commands' ? (
        <div className="panel-section">
          <h3>Command Directives</h3>
          <div className="prompt-grid">
            {playgroundCommands.map((command) => (
              <button
                key={command.title}
                className="prompt-card"
                type="button"
                onClick={() => copyPrompt(command.prompt)}
              >
                <div>
                  <span style={{ fontSize: '0.7rem', color: '#00F0FF', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    {command.category}
                  </span>
                  <strong style={{ display: 'block' }}>{command.title}</strong>
                  <p>{command.prompt}</p>
                </div>
                <Copy size={16} />
              </button>
            ))}
          </div>
          {copied && <p className="copied-note">Copied to clipboard: “{copied}”</p>}
        </div>
      ) : (
        <div className="panel-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>Confirmed Bookings</h3>
            <button
              type="button"
              onClick={fetchOrders}
              style={{
                background: 'rgba(0, 240, 255, 0.1)',
                border: '1px solid rgba(0, 240, 255, 0.3)',
                color: '#00F0FF',
                borderRadius: '6px',
                padding: '0.25rem 0.6rem',
                fontSize: '0.75rem',
                cursor: 'pointer',
              }}
            >
              Refresh
            </button>
          </div>

          {/* Demo Simulation Bar */}
          <div style={{ background: 'rgba(255, 180, 0, 0.08)', border: '1px solid rgba(255, 180, 0, 0.25)', borderRadius: '10px', padding: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#FFB400', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ⚠️ Mode: DEMO SIMULATION
              </span>
              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)' }}>Real Tickets: NO</span>
            </div>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)' }}>
              All transactions use isolated mock providers. References are prefixed with DEMO-XXXX.
            </p>
          </div>

          {loadingOrders && orders.length === 0 ? (
            <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.9rem' }}>Loading bookings grid...</p>
          ) : orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'rgba(255,255,255,0.6)' }}>
              <ShoppingBag size={32} color="#00F0FF" style={{ opacity: 0.5, marginBottom: '0.5rem' }} />
              <p style={{ margin: 0, fontSize: '0.9rem' }}>No orders yet, boss.</p>
              <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
                Ask F.R.I.D.A.Y. via voice to book a train, flight, movie, or hotel.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {orders.map((order) => (
                <div
                  key={order.order_id}
                  style={{
                    background: 'rgba(0, 240, 255, 0.05)',
                    border: '1px solid rgba(0, 240, 255, 0.2)',
                    borderRadius: '12px',
                    padding: '0.9rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {getBookingIcon(order.booking_type)}
                      <span style={{ fontSize: '0.75rem', color: '#00F0FF', textTransform: 'uppercase', fontWeight: 600 }}>
                        {order.booking_type}
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        background: order.status === 'cancelled' ? 'rgba(255,60,60,0.15)' : (order.payment_status === 'paid' ? 'rgba(0,255,160,0.15)' : 'rgba(255,180,0,0.15)'),
                        color: order.status === 'cancelled' ? '#FF6666' : (order.payment_status === 'paid' ? '#00FFA0' : '#FFB400'),
                        border: `1px solid ${order.status === 'cancelled' ? '#FF4444' : (order.payment_status === 'paid' ? '#00FFA0' : '#FFB400')}`,
                        textTransform: 'uppercase',
                      }}
                    >
                      {order.status === 'cancelled' ? 'CANCELLED' : order.payment_status}
                    </span>
                  </div>

                  <strong style={{ display: 'block', fontSize: '0.95rem', color: '#fff', marginBottom: '0.2rem' }}>
                    {order.title}
                  </strong>
                  <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.35 }}>
                    {order.description}
                  </p>

                  <div style={{ fontSize: '0.68rem', color: '#FFB400', background: 'rgba(255,180,0,0.06)', padding: '0.25rem 0.5rem', borderRadius: '4px', marginBottom: '0.5rem' }}>
                    DEMO-SIMULATION • Ref: {order.metadata?.booking_reference || order.metadata?.pnr || order.metadata?.ticket_id || order.order_id}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '0.5rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#00F0FF' }}>
                      ₹{order.amount.toLocaleString()} {order.currency}
                    </span>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      {order.status !== 'cancelled' && (
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              const r = await fetch(`${API_BASE_URL}/api/v1/bookings/${order.order_id}/cancel`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ reason: 'User clicked cancel in UI' }),
                              });
                              if (r.ok) fetchOrders();
                            } catch (error) {
                              console.error('Failed to cancel booking', error);
                            }
                          }}
                          style={{
                            background: 'transparent',
                            border: '1px solid rgba(255,100,100,0.3)',
                            color: '#FF8888',
                            fontSize: '0.72rem',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          Cancel
                        </button>
                      )}
                      {order.payment_session_id && order.payment_status !== 'paid' && order.status !== 'cancelled' && (
                        <a
                          href={`${API_BASE_URL}/api/v1/payments/${order.payment_session_id}/checkout`}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            fontSize: '0.75rem',
                            color: '#00F0FF',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            textDecoration: 'none',
                          }}
                        >
                          Checkout <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

function AssistantWorkspace({
  conversations,
  mediaAssets,
  deletingPhotoId,
  onDeletePhoto,
  activeConversationId,
  theme,
  connected,
  connecting,
  connectionState,
  error,
  onNewConversation,
  onSelectConversation,
  onUpdateMessage,
  onDeleteMessage,
  onRenameConversation,
  onDeleteConversation,
  onToggleTheme,
  sidebarCollapsed,
  onToggleSidebar,
  onSidebarPointerMove,
  onSidebarDragStart,
  onSidebarDragEnd,
  authSession,
  onSignOut,
  onOpenAuth,
  onConnect,
  onSend,
}: {
  conversations: Conversation[];
  mediaAssets: MediaAsset[];
  deletingPhotoId: string | null;
  onDeletePhoto: (asset: MediaAsset) => Promise<void>;
  activeConversationId: string | null;
  theme: AssistantTheme;
  connected: boolean;
  connecting: boolean;
  connectionState: string;
  error: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onUpdateMessage: (
    conversationId: string,
    messageId: string,
    updates: Partial<Pick<ConversationMessage, 'text' | 'feedback'>>,
  ) => void;
  onDeleteMessage: (conversationId: string, messageId: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onDeleteConversation: (id: string) => void;
  onToggleTheme: () => void;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onSidebarPointerMove: (clientX: number, pointerType: string) => void;
  onSidebarDragStart: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  onSidebarDragEnd: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  authSession: AuthSession | null;
  onSignOut: () => void;
  onOpenAuth: (mode: AuthMode) => void;
  onConnect: () => void;
  onSend: ((text: string, attachments?: File[]) => Promise<void>) | null;
}) {
  const [draft, setDraft] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [selectedPhoto, setSelectedPhoto] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [sendingPhoto, setSendingPhoto] = useState(false);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [previewPhotoId, setPreviewPhotoId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState('');
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const accountName = authSession?.user.name || 'Account signed in';
  const accountAvatarUrl = authSession?.user.avatar_url;
  const activeConversation = conversations.find(({ id }) => id === activeConversationId);
  const messages = activeConversation?.messages ?? [];

  const copyMessage = async (message: ConversationMessage) => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopiedMessageId(message.id);
    } catch (copyError) {
      console.error('Unable to copy message text', copyError);
      setSendError('Unable to copy this message. Check clipboard permissions and try again.');
    }
  };

  const deleteMessage = (message: ConversationMessage) => {
    if (!activeConversationId) return;
    if (!window.confirm(`Delete this ${message.role === 'assistant' ? 'FRIDAY response' : 'message'}?`)) return;
    onDeleteMessage(activeConversationId, message.id);
    if (editingMessageId === message.id) setEditingMessageId(null);
  };

  const saveEditedMessage = (message: ConversationMessage) => {
    if (!activeConversationId) return;
    const text = editDraft.trim();
    if (!text && !message.photoIds?.length) {
      setSendError('A message must contain text or an attached photo.');
      return;
    }
    onUpdateMessage(activeConversationId, message.id, { text });
    setEditingMessageId(null);
    setEditDraft('');
  };

  const submitMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    if ((!message && !selectedPhoto) || !connected || !onSend) return;
    setSendError(null);
    setSendingPhoto(Boolean(selectedPhoto));
    try {
      const attachments = selectedPhoto ? [await preparePhotoForUpload(selectedPhoto)] : undefined;
      await onSend(message, attachments);
      setDraft('');
      setSelectedPhoto(null);
    } catch (sendFailure) {
      setSendError(sendFailure instanceof Error ? sendFailure.message : 'Unable to send message.');
    } finally {
      setSendingPhoto(false);
    }
  };

  const selectPhoto = (file?: File) => {
    if (!file) return;
    setSendError(null);
    if (!file.type.startsWith('image/')) {
      setSendError('Choose an image file to analyze.');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setSendError('Choose a photo smaller than 20 MB.');
      return;
    }
    setSelectedPhoto(file);
  };

  useEffect(() => {
    if (!selectedPhoto) {
      setPhotoPreviewUrl(null);
      return;
    }
    const previewUrl = URL.createObjectURL(selectedPhoto);
    setPhotoPreviewUrl(previewUrl);
    return () => URL.revokeObjectURL(previewUrl);
  }, [selectedPhoto]);

  return (
    <div
      className={`assistant-shell theme-${theme} ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}
      onPointerMove={(event) => onSidebarPointerMove(event.clientX, event.pointerType)}
    >
      <aside className="history-sidebar">
        <div className="sidebar-brand">
          <img
            src="/images/friday-logo-neon.png"
            alt="FRIDAY AI Assistant"
          />
        </div>

        <button className="new-conversation-button" type="button" onClick={onNewConversation}>
          <Plus size={17} />
          <span>New conversation</span>
        </button>
        <button
          className={`media-library-button ${mediaOpen ? 'is-active' : ''}`}
          type="button"
          onClick={() => setMediaOpen((open) => !open)}
          aria-pressed={mediaOpen}
        >
          <Images size={17} />
          <span>Media</span>
          <span className="media-library-count">{mediaAssets.length}</span>
        </button>

        <div className="history-heading">
          <span>Conversations</span>
          <span className="history-count">{conversations.length}</span>
        </div>
        <nav className="conversation-list" aria-label="Conversation history">
          {conversations.length === 0 ? (
            <p className="history-empty">Your conversations will appear here.</p>
          ) : (
            conversations.map((conversation) => (
              <div
                className={`conversation-item ${conversation.id === activeConversationId ? 'is-active' : ''}`}
                key={conversation.id}
              >
                <button
                  className="conversation-select"
                  type="button"
                  onClick={() => {
                    setMediaOpen(false);
                    onSelectConversation(conversation.id);
                  }}
                  aria-current={conversation.id === activeConversationId ? 'page' : undefined}
                >
                  <MessageSquare size={15} />
                  <span>{conversation.title}</span>
                </button>
                <button
                  className="conversation-action conversation-rename"
                  type="button"
                  onClick={() => {
                    const title = window.prompt('Rename conversation', conversation.title);
                    if (title !== null) onRenameConversation(conversation.id, title);
                  }}
                  aria-label={`Rename ${conversation.title}`}
                  title="Rename conversation"
                >
                  <Pencil size={14} />
                </button>
                <button
                  className="conversation-action conversation-delete"
                  type="button"
                  onClick={() => onDeleteConversation(conversation.id)}
                  aria-label={`Delete ${conversation.title}`}
                  title="Delete conversation"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </nav>

        <div className="sidebar-bottom">
          <div className="connection-note">
            <span className={`connection-dot ${connected ? 'is-online' : ''}`} />
            <span>{connected ? (connectionState === 'listening' ? 'Listening' : 'Online') : 'Offline'}</span>
          </div>
          {authSession ? (
            <span className="sidebar-caption">Unlimited conversations available</span>
          ) : (
            <>
              <span className="sidebar-caption">
                {Math.min(conversations.length, 2)} of 2 free conversations used · Sign in for unlimited history.
              </span>
              <button className="sidebar-auth-button" type="button" onClick={() => onOpenAuth('signup')}>
                Sign up for unlimited
              </button>
            </>
          )}
        </div>
      </aside>

      <section className="assistant-main">
        <button
          className="sidebar-drag-handle"
          type="button"
          aria-label={sidebarCollapsed ? 'Open conversation sidebar' : 'Close conversation sidebar'}
          aria-expanded={!sidebarCollapsed}
          title={sidebarCollapsed ? 'Open sidebar (drag right)' : 'Close sidebar (drag left)'}
          onClick={onToggleSidebar}
          onPointerDown={onSidebarDragStart}
          onPointerUp={onSidebarDragEnd}
          onPointerCancel={onSidebarDragEnd}
        >
          <GripVertical size={13} aria-hidden="true" />
          {sidebarCollapsed
            ? <ChevronRight size={15} aria-hidden="true" />
            : <ChevronLeft size={15} aria-hidden="true" />}
        </button>
        <header className="assistant-topbar">
          <div className="topbar-title">
            <span className="topbar-kicker">PERSONAL AI ASSISTANT</span>
            <div className="topbar-brand">
              <img src="/friday-favicon.png" alt="" />
              <h1>{activeConversation?.title ?? 'FRIDAY'}</h1>
            </div>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button theme-toggle"
              type="button"
              onClick={onToggleTheme}
              aria-label={`Switch to ${theme === 'night' ? 'day' : 'night'} mode`}
              title={`Switch to ${theme === 'night' ? 'day' : 'night'} mode`}
            >
              {theme === 'night' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            {!connected && (
              authSession ? (
                <button className="connect-action" type="button" onClick={onConnect} disabled={connecting}>
                  {connecting ? 'Connecting…' : 'Connect FRIDAY'}
                </button>
              ) : (
                <button className="connect-action" type="button" onClick={() => onOpenAuth('signin')}>
                  Sign in / Sign up
                </button>
              )
            )}
            {authSession && (
              <details className="account-menu">
                <summary
                  className="account-menu-trigger"
                  title={accountName}
                  aria-label={`Account: ${accountName}`}
                >
                  <span className="account-avatar" aria-hidden="true">
                    {accountAvatarUrl && <img src={accountAvatarUrl} alt="" referrerPolicy="no-referrer" />}
                    {!accountAvatarUrl && <img src="/images/default-user-avatar.png" alt="" />}
                  </span>
                  <span className="account-menu-name">{accountName}</span>
                  <ChevronDown size={14} aria-hidden="true" />
                </summary>
                <div className="account-menu-panel">
                  <span className="account-menu-label">Signed in as</span>
                  <strong title={accountName}>{accountName}</strong>
                  {authSession.user.email && <span className="account-menu-email">{authSession.user.email}</span>}
                  <button className="account-signout-button" type="button" onClick={onSignOut}>
                    <LogOut size={14} /> Sign out
                  </button>
                </div>
              </details>
            )}
          </div>
        </header>

        <main className="chat-stage">
          <div className="grid-glow grid-glow-a" aria-hidden="true" />
          <div className="grid-glow grid-glow-b" aria-hidden="true" />
          {mediaOpen ? (
            <section className="media-library" aria-label="Uploaded photos">
              <header className="media-library-header">
                <div>
                  <p className="welcome-eyebrow">YOUR UPLOADS</p>
                  <h2>Media</h2>
                </div>
                <span>{mediaAssets.length} {mediaAssets.length === 1 ? 'photo' : 'photos'}</span>
              </header>
              {mediaAssets.length === 0 ? (
                <p className="media-library-empty">Photos you upload in chat will be collected here.</p>
              ) : (
                <div className="media-library-grid">
                  {mediaAssets.map((asset) => {
                    const conversation = conversations.find(({ id }) => id === asset.conversationId);
                    return (
                      <article className="media-library-card" key={asset.id}>
                        <button
                          className="media-library-preview"
                          type="button"
                          onClick={() => setPreviewPhotoId(asset.id)}
                          aria-label={`Preview ${asset.name}`}
                        >
                          <PhotoThumbnail photoId={asset.id} alt={asset.name} className="media-library-image" />
                        </button>
                        <div className="media-library-details">
                          <strong title={asset.name}>{asset.name}</strong>
                          <time dateTime={asset.createdAt}>
                            {new Date(asset.createdAt).toLocaleDateString()}
                          </time>
                          <div className="media-library-actions">
                            {conversation && (
                              <button
                                className="media-open-chat"
                                type="button"
                                onClick={() => {
                                  onSelectConversation(conversation.id);
                                  setMediaOpen(false);
                                }}
                              >
                                Open conversation
                              </button>
                            )}
                            <button
                              className="media-delete-button"
                              type="button"
                              onClick={() => void onDeletePhoto(asset)}
                              disabled={deletingPhotoId !== null}
                              aria-label={`Delete ${asset.name}`}
                              title={`Delete ${asset.name}`}
                            >
                              <Trash2 size={14} />
                              {deletingPhotoId === asset.id ? 'Deleting…' : 'Delete'}
                            </button>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          ) : messages.length === 0 ? (
            <div className="welcome-panel">
              <img
                className="welcome-orb"
                src={theme === 'day' ? '/images/friday-orb-light.png' : '/images/friday-orb-dark.png'}
                alt="FRIDAY neon orbital sphere"
              />
              {connected && <p className="welcome-eyebrow">SYSTEMS ONLINE</p>}
              <h2>{connected ? 'How can I help, boss?' : 'Meet your personal assistant.'}</h2>
              <p className="welcome-description">
                {connected
                  ? 'Ask by text or use your microphone for a natural voice conversation.'
                  : 'Connect to FRIDAY to start a conversation by voice or text. Your conversations stay in this browser.'}
              </p>
              {!connected && (
                <button className="welcome-connect" type="button" onClick={onConnect} disabled={connecting}>
                  {connecting ? 'Connecting…' : 'Connect to FRIDAY'}
                </button>
              )}
              <div className="suggestion-list" aria-label="Example requests">
                {['Brief me on today’s news', 'Remember a preference', 'Help me plan my day'].map((prompt) => (
                  <button
                    type="button"
                    key={prompt}
                    onClick={() => setDraft(prompt)}
                    disabled={!connected}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-thread" aria-live="polite">
              {messages.map((message) => (
                <article className={`message-row message-${message.role}`} key={message.id}>
                  <div className="message-avatar" aria-hidden="true">
                    {message.role === 'assistant'
                      ? <img src="/friday-favicon.png" alt="" />
                      : accountAvatarUrl
                        ? <img src={accountAvatarUrl} alt="" referrerPolicy="no-referrer" />
                        : <img src="/images/you-avatar.png" alt="" />}
                  </div>
                  <div className="message-content">
                    <div className="message-meta">
                      <strong>{message.role === 'assistant' ? 'FRIDAY' : 'You'}</strong>
                      <time dateTime={message.timestamp}>
                        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </time>
                    </div>
                    {editingMessageId === message.id ? (
                      <div className="message-edit">
                        <textarea
                          value={editDraft}
                          onChange={(event) => setEditDraft(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === 'Escape') {
                              setEditingMessageId(null);
                              setEditDraft('');
                            } else if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                              event.preventDefault();
                              saveEditedMessage(message);
                            }
                          }}
                          aria-label="Edit your message"
                          autoFocus
                        />
                        <div className="message-edit-actions">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingMessageId(null);
                              setEditDraft('');
                            }}
                          >
                            Cancel
                          </button>
                          <button type="button" onClick={() => saveEditedMessage(message)}>
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        {message.photoIds?.map((photoId) => (
                          <button
                            key={photoId}
                            className="chat-photo-button"
                            type="button"
                            onClick={() => setPreviewPhotoId(photoId)}
                            aria-label="View uploaded photo"
                          >
                            <PhotoThumbnail photoId={photoId} alt="Photo uploaded in this conversation" className="chat-photo" />
                          </button>
                        ))}
                        {message.role === 'assistant' ? (
                          <div className="message-answer">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalizeAssistantMarkdown(message.text)}</ReactMarkdown>
                          </div>
                        ) : (
                          <p>{message.text}</p>
                        )}
                      </>
                    )}
                    <div className="message-actions" aria-label={`${message.role === 'assistant' ? 'FRIDAY response' : 'Your message'} actions`}>
                      <button
                        className="message-action"
                        type="button"
                        onClick={() => void copyMessage(message)}
                        aria-label={copiedMessageId === message.id ? 'Copied to clipboard' : 'Copy message'}
                        title={copiedMessageId === message.id ? 'Copied' : 'Copy'}
                      >
                        <Copy size={15} />
                        <span>{copiedMessageId === message.id ? 'Copied' : 'Copy'}</span>
                      </button>
                      {message.role === 'user' ? (
                        <>
                          <button
                            className="message-action"
                            type="button"
                            onClick={() => {
                              setEditingMessageId(message.id);
                              setEditDraft(message.text);
                              setSendError(null);
                            }}
                            aria-label="Edit message"
                            title="Edit"
                          >
                            <Pencil size={15} />
                            <span>Edit</span>
                          </button>
                          <button
                            className="message-action message-action-danger"
                            type="button"
                            onClick={() => deleteMessage(message)}
                            aria-label="Delete message"
                            title="Delete"
                          >
                            <Trash2 size={15} />
                            <span>Delete</span>
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="message-action message-action-danger"
                            type="button"
                            onClick={() => deleteMessage(message)}
                            aria-label="Delete FRIDAY response"
                            title="Delete response"
                          >
                            <Trash2 size={15} />
                            <span>Delete</span>
                          </button>
                          <button
                            className={`message-action message-feedback ${message.feedback === 'positive' ? 'is-selected' : ''}`}
                            type="button"
                            onClick={() => onUpdateMessage(
                              activeConversationId ?? '',
                              message.id,
                              { feedback: message.feedback === 'positive' ? undefined : 'positive' },
                            )}
                            aria-label="Good response"
                            aria-pressed={message.feedback === 'positive'}
                            title="Good response — saved with this conversation"
                          >
                            <ThumbsUp size={15} />
                          </button>
                          <button
                            className={`message-action message-feedback ${message.feedback === 'negative' ? 'is-selected' : ''}`}
                            type="button"
                            onClick={() => onUpdateMessage(
                              activeConversationId ?? '',
                              message.id,
                              { feedback: message.feedback === 'negative' ? undefined : 'negative' },
                            )}
                            aria-label="Poor response"
                            aria-pressed={message.feedback === 'negative'}
                            title="Poor response — saved with this conversation"
                          >
                            <ThumbsDown size={15} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </article>
              ))}
              {!connected && (
                <div className="reconnect-note">
                  Reconnect to FRIDAY to continue this conversation.
                  <button type="button" onClick={onConnect} disabled={connecting}>
                    {connecting ? 'Connecting…' : 'Reconnect'}
                  </button>
                </div>
              )}
            </div>
          )}
          {previewPhotoId && (
            <div className="photo-lightbox" role="dialog" aria-modal="true" aria-label="Photo preview" onClick={() => setPreviewPhotoId(null)}>
              <button
                type="button"
                className="photo-lightbox-close"
                onClick={() => setPreviewPhotoId(null)}
                aria-label="Close photo preview"
              >
                <X size={18} />
              </button>
              <div onClick={(event) => event.stopPropagation()}>
                <PhotoThumbnail
                  photoId={previewPhotoId}
                  alt="Full-size uploaded photo"
                  className="photo-lightbox-image"
                />
              </div>
            </div>
          )}
        </main>

        <footer className="composer-area">
          {connected && (
            <div className="voice-control-row">
              <span className="voice-helper">
                <Mic size={14} />
                {connectionState === 'speaking' ? 'FRIDAY is speaking' : connectionState === 'listening' ? 'Listening for your voice' : 'Voice controls'}
              </span>
              <div className="assistant-controls">
                <VoiceAssistantControlBar />
              </div>
            </div>
          )}
          <input
            ref={imageInputRef}
            className="composer-file-input"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            aria-label="Choose a photo for FRIDAY to analyze"
            onChange={(event) => {
              selectPhoto(event.target.files?.[0]);
              event.target.value = '';
            }}
          />
          {selectedPhoto && photoPreviewUrl && (
            <div className="photo-attachment">
              <img src={photoPreviewUrl} alt="Selected photo preview" />
              <div className="photo-attachment-details">
                <strong>{selectedPhoto.name}</strong>
                <span>FRIDAY will analyze this photo and search for related information.</span>
              </div>
              <button
                type="button"
                className="remove-photo-button"
                onClick={() => setSelectedPhoto(null)}
                aria-label="Remove selected photo"
                disabled={sendingPhoto}
              >
                <Trash2 size={16} />
              </button>
            </div>
          )}
          <form className="message-composer" onSubmit={submitMessage}>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder={connected ? 'Message FRIDAY…' : 'Connect to FRIDAY to start a conversation…'}
              aria-label="Message FRIDAY"
              rows={1}
              disabled={!connected || sendingPhoto}
            />
            <button
              className="send-button"
              type="submit"
              aria-label="Send message"
              disabled={!connected || (!draft.trim() && !selectedPhoto) || sendingPhoto}
            >
              <Send size={17} />
            </button>
            <button
              className="composer-media-button"
              type="button"
              onClick={() => imageInputRef.current?.click()}
              aria-label="Add a photo for FRIDAY to analyze"
              title="Add a photo for FRIDAY to analyze"
              disabled={!connected || sendingPhoto}
            >
              <ImagePlus size={18} />
            </button>
          </form>
          {sendingPhoto && <p className="photo-status" role="status">Sending photo to FRIDAY for analysis…</p>}
          {(error || sendError) && <p className="assistant-error" role="alert">{error || sendError}</p>}
          <p className="privacy-caption">Ⓒ Agent Friday │ Het Bhadasia • Krish Rajput • Darshini Jagani</p>
        </footer>

        {connected && <RoomAudioRenderer />}
      </section>
    </div>
  );
}

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [wsUrl, setWsUrl] = useState<string>("");
  const roomName = "friday-lab";
  const [authSession, setAuthSession] = useState<AuthSession | null>(loadAuthSession);
  const initialAuthSession = useRef(authSession);
  const identity = authSession?.user.id ?? "iron-man";
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(() => {
    const callbackParams = new URLSearchParams(window.location.search);
    const isOAuthCallback = callbackParams.has('code') || callbackParams.has('error');
    return !loadAuthSession() && !isOAuthCallback;
  });
  const [authPageOpen, setAuthPageOpen] = useState(false);
  const [authPageMode, setAuthPageMode] = useState<AuthMode>('signup');
  const [authPageForced, setAuthPageForced] = useState(false);
  const [googleAuthError, setGoogleAuthError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>(
    () => loadConversations(loadAuthSession()?.user.id),
  );
  const [mediaAssets, setMediaAssets] = useState<MediaAsset[]>([]);
  const [deletingPhotoId, setDeletingPhotoId] = useState<string | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    () => loadConversations(loadAuthSession()?.user.id)[0]?.id ?? null,
  );
  const activeConversationIdRef = useRef(activeConversationId);
  const authOperationRef = useRef(0);
  const googleCallbackHandledRef = useRef(false);
  const handleAuthenticatedRef = useRef<(session: AuthSession, mode: AuthMode) => void>(() => {});
  const hydratedUserIdRef = useRef<string | null>(null);
  const [theme, setTheme] = useState<AssistantTheme>(storedTheme);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const sidebarPointerStart = useRef<{ x: number; y: number } | null>(null);
  const suppressSidebarClick = useRef(false);
  const suppressSidebarHoverRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setMediaAssets([]);
    void getMediaAssets(identity).then((assets) => {
      if (!cancelled) setMediaAssets(assets);
    }).catch((loadError: unknown) => {
      if (cancelled) return;
      console.error('Unable to load the photo library', loadError);
      setError(
        loadError instanceof Error
          ? `Unable to load your photo library: ${loadError.message}`
          : 'Unable to load your photo library.',
      );
    });
    return () => { cancelled = true; };
  }, [identity]);

  const hydrateUserConversations = async (
    session: AuthSession,
    localConversations: Conversation[],
    operation: number,
    isCancelled: () => boolean = () => false,
  ) => {
    let cloudConversations: Conversation[];
    try {
      cloudConversations = await getSavedConversations(session);
    } catch (loadError) {
      if (operation !== authOperationRef.current || isCancelled()) return;
      console.error('Unable to load saved conversations from the server', loadError);
      setError(
        loadError instanceof Error
          ? `${loadError.message} Your browser copy is still available.`
          : 'Unable to load cloud conversation history. Your browser copy is still available.',
      );
      return;
    }

    if (operation !== authOperationRef.current || isCancelled()) return;
    const conversationsToUse = cloudConversations.length > 0
      ? cloudConversations
      : localConversations;
    hydratedUserIdRef.current = session.user.id;
    const nextId = conversationsToUse[0]?.id ?? null;
    activeConversationIdRef.current = nextId;
    setConversations(conversationsToUse);
    setActiveConversationId(nextId);
    setError(null);

    if (cloudConversations.length === 0 && localConversations.length > 0) {
      try {
        for (const conversation of localConversations) {
          await putSavedConversation(session, conversation);
        }
      } catch (saveError) {
        if (operation !== authOperationRef.current || isCancelled()) return;
        console.error('Unable to migrate local conversation history to the server', saveError);
        setError(
          saveError instanceof Error
            ? `${saveError.message} Your browser copy is still available.`
            : 'Unable to copy local chats to cloud storage. Your browser copy is still available.',
        );
      }
    }
  };

  useEffect(() => {
    const callbackParams = new URLSearchParams(window.location.search);
    if (callbackParams.has('code') || callbackParams.has('error')) return;
    const savedSession = initialAuthSession.current;
    if (!savedSession) {
      setAuthReady(true);
      return;
    }
    let cancelled = false;
    const operation = ++authOperationRef.current;
    let sessionRejected = false;
    let session = savedSession;
    const restoreSession = async () => {
      try {
        if (session.expires_at * 1000 <= Date.now() + 30_000) {
          const refreshResponse = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: session.refresh_token }),
          });
          const refreshData = await refreshResponse.json();
          if (!refreshResponse.ok) {
            sessionRejected = refreshResponse.status === 401;
            throw new Error(refreshData.error || 'Please sign in again.');
          }
          const refreshedSession = toAuthSession(refreshData);
          session = {
            ...refreshedSession,
            user: {
              ...refreshedSession.user,
              avatar_url: refreshedSession.user.avatar_url ?? session.user.avatar_url,
            },
          };
        } else {
          const validationResponse = await fetch(`${API_BASE_URL}/api/auth/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: session.access_token }),
          });
          if (!validationResponse.ok) {
            sessionRejected = validationResponse.status === 401;
            throw new Error(
              sessionRejected
                ? 'Your session has expired. Please sign in again.'
                : 'Unable to validate your session. Check your connection and try again.',
            );
          }
        }
        if (cancelled) return;
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
        setAuthSession(session);
        await hydrateUserConversations(
          session,
          loadConversations(session.user.id),
          operation,
          () => cancelled,
        );
      } catch (restoreError) {
        if (cancelled) return;
        console.error('Unable to restore authentication session', restoreError);
        if (sessionRejected) {
          hydratedUserIdRef.current = null;
          try {
            localStorage.removeItem(AUTH_STORAGE_KEY);
          } catch (storageError) {
            console.error('Unable to remove the expired authentication session', storageError);
          }
          setAuthSession(null);
          const guestConversations = loadConversations();
          setConversations(guestConversations);
          const nextId = guestConversations[0]?.id ?? null;
          activeConversationIdRef.current = nextId;
          setActiveConversationId(nextId);
        } else {
          setAuthSession(session);
          hydratedUserIdRef.current = null;
          const savedConversations = loadConversations(session.user.id);
          setConversations(savedConversations);
          const nextId = savedConversations[0]?.id ?? null;
          activeConversationIdRef.current = nextId;
          setActiveConversationId(nextId);
          setError(
            restoreError instanceof Error
              ? restoreError.message
              : 'Unable to validate your session. Check your connection and try again.',
          );
        }
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    };
    void restoreSession();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(conversationStorageKey(authSession?.user.id), JSON.stringify(conversations));
    } catch (storageError) {
      console.error('Unable to save conversations', storageError);
      setError('Conversation history could not be saved in this browser.');
    }
  }, [authSession?.user.id, conversations]);

  useEffect(() => {
    if (!authSession || hydratedUserIdRef.current !== authSession.user.id) return;
    const session = authSession;
    const snapshot = conversations;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          for (const conversation of snapshot) {
            await putSavedConversation(session, conversation);
          }
        } catch (saveError) {
          console.error('Unable to sync conversation history to the server', saveError);
          setError(
            saveError instanceof Error
              ? `${saveError.message} Your browser copy is still available.`
              : 'Unable to sync cloud conversation history. Your browser copy is still available.',
          );
        }
      })();
    }, 500);
    return () => window.clearTimeout(timer);
  }, [authSession, conversations]);

  useEffect(() => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (storageError) {
      console.error('Unable to save theme preference', storageError);
    }
  }, [theme]);

  const saveMessage = useCallback((
    conversationId: string,
    role: MessageRole,
    text: string,
    timestamp: number,
    attachments?: File[],
  ): Promise<void> => {
    const save = async () => {
      const currentId = conversationId || activeConversationIdRef.current;
      const newConversation = currentId ? null : createConversation();
      const id = currentId || newConversation?.id;
      if (!id) return;
      const messageId = `${role}-${timestamp}`;
      const savedAssets = await Promise.all((attachments ?? []).map(async (file, index) => {
        const asset: MediaAsset = {
          id: `photo-${messageId}-${index}`,
          ownerId: identity,
          conversationId: id,
          messageId,
          name: file.name,
          mimeType: file.type || 'image/jpeg',
          createdAt: new Date(timestamp).toISOString(),
          blob: file,
        };
        await saveMediaAsset(asset);
        return asset;
      }));
      if (savedAssets.length) {
        setMediaAssets((current) => [
          ...savedAssets,
          ...current.filter((asset) => !savedAssets.some((saved) => saved.id === asset.id)),
        ]);
      }
      activeConversationIdRef.current = id;
      setActiveConversationId(id);
      setConversations((current) => {
        const existing = current.find((conversation) => conversation.id === id);
        const message: ConversationMessage = {
          id: messageId,
          role,
          text,
          timestamp: new Date(timestamp).toISOString(),
          photoIds: savedAssets.map((asset) => asset.id),
        };
        const previousMessages = existing?.messages ?? [];
        const currentMessage = previousMessages.find((item) => item.id === message.id);
        const messages = currentMessage
          ? previousMessages.map((item) => item.id === message.id ? {
            ...message,
            photoIds: [...new Set([...(item.photoIds ?? []), ...(message.photoIds ?? [])])],
          } : item)
          : [...previousMessages, message];
        const conversation: Conversation = {
          id,
          title: existing?.title ?? (role === 'user' ? text.slice(0, 42) : 'New conversation'),
          updatedAt: message.timestamp,
          messages,
        };
        return [conversation, ...current.filter((item) => item.id !== id)];
      });
    };
    return save().catch((saveError: unknown) => {
      console.error('Unable to save a chat message or its photo', saveError);
      setError(
        saveError instanceof Error
          ? `Message received, but its photo could not be saved: ${saveError.message}`
          : 'Message received, but its photo could not be saved.',
      );
    });
  }, [identity]);

  const updateConversationMessage = (
    conversationId: string,
    messageId: string,
    updates: Partial<Pick<ConversationMessage, 'text' | 'feedback'>>,
  ) => {
    if (!conversationId) return;
    setConversations((current) => current.map((conversation) => {
      if (conversation.id !== conversationId) return conversation;
      return {
        ...conversation,
        updatedAt: new Date().toISOString(),
        messages: conversation.messages.map((message) =>
          message.id === messageId ? { ...message, ...updates } : message,
        ),
      };
    }));
  };

  const deleteConversationMessage = (conversationId: string, messageId: string) => {
    if (!conversationId) return;
    setConversations((current) => current.map((conversation) => {
      if (conversation.id !== conversationId) return conversation;
      const deletedMessage = conversation.messages.find((message) => message.id === messageId);
      const messages = conversation.messages.filter((message) => message.id !== messageId);
      const titleMatchesDeletedMessage = deletedMessage?.role === 'user'
        && conversation.title === deletedMessage.text.slice(0, 42);
      const nextUserMessage = messages.find((message) => message.role === 'user');
      return {
        ...conversation,
        title: titleMatchesDeletedMessage
          ? nextUserMessage?.text.slice(0, 42) || 'New conversation'
          : conversation.title,
        updatedAt: new Date().toISOString(),
        messages,
      };
    }));
  };

  const deletePhoto = async (asset: MediaAsset) => {
    if (!window.confirm(`Delete "${asset.name}" from Media and remove it from its conversation?`)) {
      return;
    }

    setDeletingPhotoId(asset.id);
    setError(null);
    try {
      await deleteMediaAsset(asset.id);
      setMediaAssets((current) => current.filter((item) => item.id !== asset.id));
      setConversations((current) => current.map((conversation) => {
        const hasPhoto = conversation.messages.some((message) => message.photoIds?.includes(asset.id));
        if (!hasPhoto) return conversation;
        return {
          ...conversation,
          messages: conversation.messages.map((message) => message.photoIds?.includes(asset.id)
            ? { ...message, photoIds: message.photoIds.filter((photoId) => photoId !== asset.id) }
            : message),
        };
      }));
    } catch (deleteError) {
      console.error('Unable to delete photo from the media library', deleteError);
      setError(
        deleteError instanceof Error
          ? `Unable to delete "${asset.name}": ${deleteError.message}`
          : `Unable to delete "${asset.name}".`,
      );
    } finally {
      setDeletingPhotoId(null);
    }
  };

  const openAuthPage = (mode: AuthMode, forced = false) => {
    setAuthPageMode(mode);
    setAuthPageForced(forced);
    setAuthPageOpen(true);
  };
  const startNewConversation = () => {
    if (!authSession && conversations.length >= 2) {
      openAuthPage('signup', true);
      return;
    }
    const conversation = createConversation();
    activeConversationIdRef.current = conversation.id;
    setActiveConversationId(conversation.id);
    setConversations((current) => [conversation, ...current]);
  };
  const selectConversation = (id: string) => {
    activeConversationIdRef.current = id;
    setActiveConversationId(id);
  };
  const toggleTheme = () => setTheme((current) => current === 'night' ? 'day' : 'night');
  const toggleSidebar = () => {
    if (suppressSidebarClick.current) {
      suppressSidebarClick.current = false;
      return;
    }
    setSidebarCollapsed((current) => {
      suppressSidebarHoverRef.current = !current;
      return !current;
    });
  };
  const handleSidebarPointerMove = (clientX: number, pointerType: string) => {
    if (pointerType === 'touch' || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (clientX > 36) {
      suppressSidebarHoverRef.current = false;
      return;
    }
    if (sidebarCollapsed && !suppressSidebarHoverRef.current) setSidebarCollapsed(false);
  };
  const startSidebarDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    sidebarPointerStart.current = { x: event.clientX, y: event.clientY };
    suppressSidebarClick.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const endSidebarDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const start = sidebarPointerStart.current;
    if (start === null) return;
    const isMobile = window.matchMedia('(max-width: 600px)').matches;
    const delta = isMobile ? event.clientY - start.y : event.clientX - start.x;
    sidebarPointerStart.current = null;
    if (Math.abs(delta) < 42) return;
    const draggedToClose = delta < 0;
    suppressSidebarHoverRef.current = draggedToClose;
    setSidebarCollapsed(draggedToClose);
    suppressSidebarClick.current = true;
  };
  const deleteConversation = (id: string) => {
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
    if (authSession && hydratedUserIdRef.current === authSession.user.id) {
      void deleteSavedConversation(authSession, id).catch((deleteError: unknown) => {
        console.error('Unable to delete conversation from the server', deleteError);
        setError(
          deleteError instanceof Error
            ? deleteError.message
            : 'Unable to delete the saved conversation from cloud history.',
        );
      });
    }
    if (activeConversationIdRef.current === id) {
      activeConversationIdRef.current = null;
      setActiveConversationId(null);
    }
  };
  const renameConversation = (id: string, title: string) => {
    const nextTitle = title.trim().slice(0, 255);
    if (!nextTitle) return;
    setConversations((current) => current.map((conversation) =>
      conversation.id === id
        ? { ...conversation, title: nextTitle, updatedAt: new Date().toISOString() }
        : conversation,
    ));
  };

  const handleAuthenticated = (session: AuthSession, mode: AuthMode) => {
    const operation = ++authOperationRef.current;
    hydratedUserIdRef.current = null;
    let persistenceWarning: string | null = null;
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    } catch (storageError) {
      console.error('Unable to persist authentication session', storageError);
      persistenceWarning = 'You are signed in, but your session could not be remembered in this browser.';
    }
    const savedUserConversations = loadConversations(session.user.id);
    const shouldMigrateGuestHistory = mode === 'signup' && savedUserConversations.length === 0;
    const localConversations = shouldMigrateGuestHistory
      ? loadConversations()
      : savedUserConversations;
    if (shouldMigrateGuestHistory) {
      try {
        localStorage.setItem(conversationStorageKey(session.user.id), JSON.stringify(localConversations));
      } catch (storageError) {
        console.error('Unable to migrate guest conversations to the new account', storageError);
        persistenceWarning = 'Your account was created, but the free conversation history could not be copied.';
      }
    }
    setAuthSession(session);
    const localNextId = localConversations[0]?.id ?? null;
    activeConversationIdRef.current = localNextId;
    setConversations(localConversations);
    setActiveConversationId(localNextId);
    setAuthPageOpen(false);
    setAuthPageForced(false);
    setError(persistenceWarning);
    void hydrateUserConversations(session, localConversations, operation);
  };
  handleAuthenticatedRef.current = handleAuthenticated;

  const startGoogleSignIn = async () => {
    setGoogleAuthError(null);
    const client = await getSupabaseAuthClient();
    const { error: oauthError } = await client.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
        queryParams: { prompt: 'select_account' },
      },
    });
    if (oauthError) throw oauthError;
  };

  useEffect(() => {
    const callbackParams = new URLSearchParams(window.location.search);
    const authorizationCode = callbackParams.get('code');
    const providerError = callbackParams.get('error_description') || callbackParams.get('error');
    if ((!authorizationCode && !providerError) || googleCallbackHandledRef.current) return;
    googleCallbackHandledRef.current = true;
    window.history.replaceState({}, document.title, `${window.location.pathname}${window.location.hash}`);

    const completeGoogleSignIn = async () => {
      try {
        if (providerError) throw new Error(providerError);
        if (!authorizationCode) throw new Error('Google did not return an authorization code.');
        const client = await getSupabaseAuthClient();
        const { data, error: exchangeError } = await client.auth.exchangeCodeForSession(authorizationCode);
        if (exchangeError) throw exchangeError;
        const providerAccessToken = data.session?.access_token;
        if (!providerAccessToken) {
          throw new Error('Google sign-in did not return a valid session.');
        }

        const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: providerAccessToken }),
        });
        const sessionData: {
          error?: string;
          access_token?: string;
          refresh_token?: string;
          expires_in?: number;
          expires_at?: number;
          user?: AuthUser;
        } = await response.json();
        if (!response.ok) throw new Error(sessionData.error || 'Unable to finish Google sign-in.');
        const providerProfile = data.session?.user.user_metadata;
        const avatarUrl = getProfileAvatarUrl(providerProfile?.avatar_url ?? providerProfile?.picture);
        const session = toAuthSession(sessionData);
        handleAuthenticatedRef.current({
          ...session,
          user: { ...session.user, ...(avatarUrl ? { avatar_url: avatarUrl } : {}) },
        }, 'signin');
      } catch (callbackError) {
        setGoogleAuthError(
          callbackError instanceof Error ? callbackError.message : 'Unable to finish Google sign-in.',
        );
        setAuthPageMode('signin');
        setAuthPageOpen(true);
      } finally {
        setAuthReady(true);
      }
    };

    void completeGoogleSignIn();
  }, []);

  const handleSignOut = () => {
    authOperationRef.current += 1;
    hydratedUserIdRef.current = null;
    let signOutWarning: string | null = null;
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch (storageError) {
      console.error('Unable to remove the saved authentication session', storageError);
      signOutWarning = 'This browser could not forget the saved session. Please clear site data before sharing this device.';
    }
    setToken(null);
    setWsUrl('');
    const guestConversations = loadConversations();
    const nextId = guestConversations[0]?.id ?? null;
    activeConversationIdRef.current = nextId;
    setAuthSession(null);
    setConversations(guestConversations);
    setActiveConversationId(nextId);
    openAuthPage('signin');
    setError(signOutWarning);
  };

  const connectToFriday = async () => {
    setConnecting(true);
    setError(null);
    try {
      const authenticatedRoomName = authSession ? `friday-${authSession.user.id}` : roomName;
      const query = new URLSearchParams({ room_name: authenticatedRoomName, identity });
      const headers: HeadersInit = authSession
        ? { Authorization: `Bearer ${authSession.access_token}` }
        : {};
      const res = await fetch(`${API_BASE_URL}/api/token?${query}`, { headers });
      if (!res.ok) {
        throw new Error('Failed to get connection token. Ensure the token server is running at :8080.');
      }
      const data = await res.json();
      setToken(data.token);
      setWsUrl(data.url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to connect to FRIDAY.');
    } finally {
      setConnecting(false);
    }
  };

  const workspaceProps = {
    conversations,
    mediaAssets,
    deletingPhotoId,
    onDeletePhoto: deletePhoto,
    onUpdateMessage: updateConversationMessage,
    onDeleteMessage: deleteConversationMessage,
    activeConversationId,
    theme,
    connecting,
    error,
    onNewConversation: startNewConversation,
    onSelectConversation: selectConversation,
    onRenameConversation: renameConversation,
    onDeleteConversation: deleteConversation,
    onToggleTheme: toggleTheme,
    sidebarCollapsed,
    onToggleSidebar: toggleSidebar,
    onSidebarPointerMove: handleSidebarPointerMove,
    onSidebarDragStart: startSidebarDrag,
    onSidebarDragEnd: endSidebarDrag,
    authSession,
    onSignOut: handleSignOut,
    onOpenAuth: openAuthPage,
    onConnect: connectToFriday,
  };

  if (!authReady) {
    return <main className={`auth-page theme-${theme}`}><div className="loader" aria-label="Restoring session" /></main>;
  }

  if (authPageOpen) {
    return (
      <div className={`assistant-shell theme-${theme}`}>
        <AuthPage
          theme={theme}
          mode={authPageMode}
          forced={authPageForced}
          onModeChange={setAuthPageMode}
          onBack={() => setAuthPageOpen(false)}
          onAuthenticated={handleAuthenticated}
          onGoogleSignIn={startGoogleSignIn}
          googleError={googleAuthError}
        />
      </div>
    );
  }

  if (token && wsUrl) {
    return (
      <LiveKitRoom
        serverUrl={wsUrl}
        token={token}
        connect={true}
        audio={true}
        video={false}
        className="main-room"
        onDisconnected={() => setToken(null)}
      >
        <ConnectedWorkspace identity={identity} activeConversationId={activeConversationId} onMessage={saveMessage}>
          {(connectionState, sendMessage) => (
            <AssistantWorkspace
              {...workspaceProps}
              connected={true}
              connectionState={connectionState}
              onSend={sendMessage}
            />
          )}
        </ConnectedWorkspace>
      </LiveKitRoom>
    );
  }

  return (
    <AssistantWorkspace
      {...workspaceProps}
      connected={false}
      connectionState="disconnected"
      onSend={null}
    />
  );
}

export default App;
