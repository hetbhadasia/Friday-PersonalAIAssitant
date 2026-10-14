import { useState, useEffect } from 'react';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  BarVisualizer,
  useVoiceAssistant,
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
} from 'lucide-react';
import '@livekit/components-styles';

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

function FridayDashboard() {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="stark-container">
      <div className="corner-brand">
        <img src="/friday-wordmark.png" alt="FRIDAY" />
      </div>
      <main className="main-interface voice-console">
        <div className="console-intro">
          <h2>F.R.I.D.A.Y.</h2>
          <p>Speak naturally. I’m listening whenever you’re ready.</p>
        </div>

        <div className={`voice-stage voice-stage-${state}`}>
          <div className="voice-orbit voice-orbit-outer" aria-hidden="true" />
          <div className="voice-orbit voice-orbit-inner" aria-hidden="true" />
          <div className="voice-core">
            <div className="lk-agent-visualizer">
              <BarVisualizer
                state={state}
                barCount={7}
                options={{ minHeight: 12 }}
                trackRef={audioTrack}
              />
            </div>
          </div>
        </div>

        <div className="assistant-status">
          <span className="status-indicator" />
          <span className="agent-state">
            {state === 'initializing' && 'Initializing Core Systems...'}
            {state === 'listening' && 'Listening'}
            {state === 'thinking' && 'Thinking'}
            {state === 'speaking' && 'Speaking'}
            {state === 'disconnected' && 'Disconnected from host'}
          </span>
        </div>

        <div className="assistant-controls">
          <VoiceAssistantControlBar />
        </div>
      </main>

      <RoomAudioRenderer />
    </div>
  );
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
      const res = await fetch("http://127.0.0.1:8080/api/v1/bookings");
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
                              const r = await fetch(`http://127.0.0.1:8080/api/v1/bookings/${order.order_id}/cancel`, {
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
                          href={`http://127.0.0.1:8080/api/v1/payments/${order.payment_session_id}/checkout`}
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

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [wsUrl, setWsUrl] = useState<string>("");
  const roomName = "friday-lab";
  const identity = "iron-man";
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connectToFriday = async () => {
    setConnecting(true);
    setError(null);
    try {
      const query = new URLSearchParams({ room_name: roomName, identity });
      const res = await fetch(`http://127.0.0.1:8080/api/token?${query}`);
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

  if (!token || !wsUrl) {
    return (
      <div className="connection-screen">
        <img className="connection-logo" src="/friday-wordmark.png" alt="FRIDAY" />
        <p className="subheading" style={{ marginBottom: '1.5rem' }}>
          I am FRIDAY, your personal AI assistant.
        </p>

        {error && <p className="error-text">{error}</p>}

        {connecting ? (
          <div className="loader"></div>
        ) : (
          <button className="connect-btn" onClick={connectToFriday}>
            Talk To FRIDAY
          </button>
        )}
      </div>
    );
  }

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
      <FridayDashboard />
    </LiveKitRoom>
  );
}

export default App;
