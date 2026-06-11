import { useState, useEffect, useRef } from 'react';
import { getSheets, getSheetData } from '../api';
import DataTable from '../components/DataTable';
import AdminPanel from './AdminPanel';
import LogsPanel from './LogsPanel';
import './Dashboard.css';

export default function Dashboard({ user, token, onLogout }) {
    const [sheets, setSheets] = useState([]);
    const [groupOrder, setGroupOrder] = useState([]); // ordered list of source_sheet group names
    const [activeSheet, setActiveSheet] = useState(null);
    const [expandedGroups, setExpandedGroups] = useState({});
    const dragGroup = useRef(null);
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isStale, setIsStale] = useState(false);
    const [view, setView] = useState('data');

    useEffect(() => {
        getSheets(token)
            .then(data => {
                setSheets(data);
                const groups = {};
                const order = [];
                data.forEach(s => {
                    if (s.source_sheet && !groups[s.source_sheet]) {
                        groups[s.source_sheet] = true;
                        order.push(s.source_sheet);
                    }
                });
                setExpandedGroups(groups);
                setGroupOrder(order);
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

    // Auto-refresh active sheet every 15 seconds
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
        }, 15000);
        return () => clearInterval(interval);
    }, [activeSheet]);

    // Retry loading the sheets list every 15s if it failed on mount (e.g. DB was down)
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
        }, 15000);
        return () => clearInterval(interval);
    }, [sheets.length]);

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <span className="dashboard-brand">Monex</span>
                <div className="dashboard-user">
                    <span>{user.username}</span>
                    <button className="logout-btn" onClick={onLogout}>Cerrar sesión</button>
                </div>
            </header>

            <div className="dashboard-body">
                <nav className="sidebar">
                    <p className="sidebar-label">Tablas</p>
                    {sheets.length === 0 && (
                        <p className="sidebar-empty">Tablas no sincronizadas.</p>
                    )}
                    {(() => {
                        const grouped = {};
                        const ungrouped = [];
                        sheets.forEach(s => {
                            if (s.source_sheet) {
                                if (!grouped[s.source_sheet]) grouped[s.source_sheet] = [];
                                grouped[s.source_sheet].push(s);
                            } else {
                                ungrouped.push(s);
                            }
                        });

                        function onDragStart(e, group) {
                            dragGroup.current = group;
                            e.dataTransfer.effectAllowed = 'move';
                        }
                        function onDragOver(e, group) {
                            e.preventDefault();
                            if (!dragGroup.current || dragGroup.current === group) return;
                            setGroupOrder(prev => {
                                const next = [...prev];
                                const from = next.indexOf(dragGroup.current);
                                const to = next.indexOf(group);
                                if (from === -1 || to === -1) return prev;
                                next.splice(from, 1);
                                next.splice(to, 0, dragGroup.current);
                                return next;
                            });
                        }
                        function onDragEnd() { dragGroup.current = null; }

                        const orderedGroups = groupOrder.filter(g => grouped[g]);

                        return (
                            <>
                                {orderedGroups.map(group => (
                                    <div
                                        key={group}
                                        draggable
                                        onDragStart={e => onDragStart(e, group)}
                                        onDragOver={e => onDragOver(e, group)}
                                        onDragEnd={onDragEnd}
                                        className="sidebar-group-wrapper"
                                    >
                                        <button
                                            className="sidebar-group"
                                            onClick={() => setExpandedGroups(g => ({ ...g, [group]: !g[group] }))}
                                        >
                                            <span className="sidebar-drag-handle">⠿</span>
                                            <span className="sidebar-group-arrow">{expandedGroups[group] ? '▾' : '▸'}</span>
                                            {group}
                                        </button>
                                        {expandedGroups[group] && grouped[group].map(sheet => (
                                            <button
                                                key={sheet.id}
                                                className={`sidebar-item sidebar-subitem ${view === 'data' && activeSheet?.id === sheet.id ? 'active' : ''}`}
                                                onClick={() => selectSheet(sheet)}
                                            >
                                                {sheet.display_name || sheet.name}
                                            </button>
                                        ))}
                                    </div>
                                ))}
                                {ungrouped.map(sheet => (
                                    <button
                                        key={sheet.id}
                                        className={`sidebar-item ${view === 'data' && activeSheet?.id === sheet.id ? 'active' : ''}`}
                                        onClick={() => selectSheet(sheet)}
                                    >
                                        {sheet.display_name || sheet.name}
                                    </button>
                                ))}
                            </>
                        );
                    })()}

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
                            {loading && <p className="dash-loading">Cargando...</p>}
                            {sheetData && !loading && (
                                <DataTable
                                    sheet={sheetData.sheet}
                                    rows={sheetData.rows}
                                />
                            )}
                            {!activeSheet && !loading && sheets.length === 0 && (
                                <p className="dash-empty">
                                    Ejecuta el script de sincronización para cargar datos desde Excel.
                                </p>
                            )}
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}
