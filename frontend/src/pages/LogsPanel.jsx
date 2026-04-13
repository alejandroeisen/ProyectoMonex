import { useState, useEffect, useRef } from 'react';
import { getStatus } from '../api';
import './LogsPanel.css';

const REFRESH_INTERVAL = 10_000;
const STALE_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
}

function staleness(isoTimestamp) {
    if (!isoTimestamp) return 'unknown';
    const age = Date.now() - new Date(isoTimestamp).getTime();
    if (age > STALE_THRESHOLD_MS) return 'stale';
    return 'ok';
}

export default function LogsPanel({ token }) {
    const [status, setStatus] = useState(null);
    const [error, setError] = useState('');
    const [lastChecked, setLastChecked] = useState(null);
    const logRef = useRef(null);

    async function fetchStatus() {
        try {
            const data = await getStatus(token);
            setStatus(data);
            setLastChecked(new Date());
            setError('');
        } catch (err) {
            setError(err.message);
        }
    }

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, REFRESH_INTERVAL);
        return () => clearInterval(interval);
    }, []);

    // Scroll log to bottom when lines update
    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [status?.log_lines]);

    const syncStatus = status ? staleness(status.last_sync_at) : null;

    return (
        <div className="logs-panel">
            {error && <p className="logs-error">{error}</p>}

            <div className="logs-status-bar">
                <div className="status-card">
                    <span className="status-label">Database</span>
                    {status === null
                        ? <span className="status-pill pill-unknown">—</span>
                        : status.db_ok
                            ? <span className="status-pill pill-ok">Connected</span>
                            : <span className="status-pill pill-error">Offline</span>
                    }
                    {status?.db_error && (
                        <span className="stale-warning">{status.db_error.split('\n')[0]}</span>
                    )}
                </div>

                <div className="status-card">
                    <span className="status-label">Last sync</span>
                    <span className={`status-pill ${syncStatus === 'stale' ? 'pill-warn' : syncStatus === 'ok' ? 'pill-ok' : 'pill-unknown'}`}>
                        {status ? formatDate(status.last_sync_at) : '—'}
                    </span>
                    {syncStatus === 'stale' && (
                        <span className="stale-warning">Sync may be stopped</span>
                    )}
                </div>

                {lastChecked && (
                    <span className="logs-refreshed">
                        Refreshes every 10s · last checked {lastChecked.toLocaleTimeString()}
                    </span>
                )}
            </div>

            {status?.sheets?.length > 0 && (
                <div className="sheet-counts">
                    <p className="logs-section-title">Sheets</p>
                    <table className="counts-table">
                        <thead>
                            <tr>
                                <th>Sheet</th>
                                <th>Rows</th>
                                <th>Last synced</th>
                            </tr>
                        </thead>
                        <tbody>
                            {status.sheets.map(s => (
                                <tr key={s.name}>
                                    <td>{s.display_name || s.name}</td>
                                    <td>{s.row_count}</td>
                                    <td>{formatDate(s.last_synced_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="log-section">
                <p className="logs-section-title">Sync log (last 80 lines)</p>
                {status?.log_missing ? (
                    <p className="logs-empty">
                        No log file found. Run the sync script once to generate it.
                    </p>
                ) : (
                    <pre className="log-output" ref={logRef}>
                        {status?.log_lines?.length
                            ? status.log_lines.join('\n')
                            : 'No log entries yet.'}
                    </pre>
                )}
            </div>
        </div>
    );
}
