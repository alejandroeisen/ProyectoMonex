import { useState, useEffect } from 'react';
import { getSheets, getSheetData } from '../api';
import DataTable from '../components/DataTable';
import AdminPanel from './AdminPanel';
import LogsPanel from './LogsPanel';
import './Dashboard.css';

export default function Dashboard({ user, token, onLogout }) {
    const [sheets, setSheets] = useState([]);
    const [activeSheet, setActiveSheet] = useState(null);
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isStale, setIsStale] = useState(false);
    const [view, setView] = useState('data');

    useEffect(() => {
        getSheets(token)
            .then(data => {
                setSheets(data);
                if (data.length > 0) selectSheet(data[0]);
            })
            .catch(err => setError(err.message));
    }, []);

    async function selectSheet(sheet) {
        setView('data');
        setActiveSheet(sheet);
        setSheetData(null);
        setLoading(true);
        setError('');
        setIsStale(false);
        try {
            const data = await getSheetData(token, sheet.id);
            setSheetData(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    // Auto-refresh active sheet every 5 seconds
    useEffect(() => {
        if (!activeSheet) return;
        const interval = setInterval(async () => {
            try {
                const data = await getSheetData(token, activeSheet.id);
                setSheetData(data);
                setIsStale(false);
            } catch {
                // Keep showing last known data, flag it as potentially stale
                setIsStale(true);
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [activeSheet]);

    // Retry loading the sheets list every 10s if it failed on mount (e.g. DB was down)
    useEffect(() => {
        if (sheets.length > 0) return;
        const interval = setInterval(() => {
            getSheets(token)
                .then(data => {
                    if (data.length > 0) {
                        setSheets(data);
                        selectSheet(data[0]);
                    }
                })
                .catch(() => {});
        }, 10000);
        return () => clearInterval(interval);
    }, [sheets.length]);

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <span className="dashboard-brand">Intelimed</span>
                <div className="dashboard-user">
                    <span>{user.username}</span>
                    <button className="logout-btn" onClick={onLogout}>Sign out</button>
                </div>
            </header>

            <div className="dashboard-body">
                <nav className="sidebar">
                    <p className="sidebar-label">Tables</p>
                    {sheets.length === 0 && (
                        <p className="sidebar-empty">No data synced yet</p>
                    )}
                    {sheets.map(sheet => (
                        <button
                            key={sheet.id}
                            className={`sidebar-item ${view === 'data' && activeSheet?.id === sheet.id ? 'active' : ''}`}
                            onClick={() => selectSheet(sheet)}
                        >
                            {sheet.display_name || sheet.name}
                        </button>
                    ))}

                    {user.role === 'admin' && (
                        <>
                            <button
                                className={`sidebar-item sidebar-admin-tab ${view === 'admin' ? 'active' : ''}`}
                                onClick={() => setView('admin')}
                            >
                                Admin
                            </button>
                            <button
                                className={`sidebar-item sidebar-admin-tab ${view === 'logs' ? 'active' : ''}`}
                                onClick={() => setView('logs')}
                            >
                                Logs
                            </button>
                        </>
                    )}
                </nav>

                <main className="dashboard-main">
                    {view === 'admin' ? (
                        <AdminPanel token={token} />
                    ) : view === 'logs' ? (
                        <LogsPanel token={token} />
                    ) : (
                        <>
                            {isStale && (
                                <div className="stale-banner">
                                    ⚠ No se pudo actualizar — sin conexión a la base de datos. Los precios mostrados pueden no estar al día.
                                </div>
                            )}
                            {error && !sheetData && <p className="dash-error">{error}</p>}
                            {loading && <p className="dash-loading">Loading...</p>}
                            {sheetData && !loading && (
                                <DataTable
                                    sheet={sheetData.sheet}
                                    rows={sheetData.rows}
                                />
                            )}
                            {!activeSheet && !loading && sheets.length === 0 && (
                                <p className="dash-empty">
                                    Run the sync script to load data from Excel.
                                </p>
                            )}
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}
