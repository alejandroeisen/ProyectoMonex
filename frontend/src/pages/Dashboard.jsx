import { useState, useEffect } from 'react';
import { getSheets, getSheetData } from '../api';
import DataTable from '../components/DataTable';
import './Dashboard.css';

export default function Dashboard({ user, token, onLogout }) {
    const [sheets, setSheets] = useState([]);
    const [activeSheet, setActiveSheet] = useState(null);
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        getSheets(token)
            .then(data => {
                setSheets(data);
                if (data.length > 0) selectSheet(data[0]);
            })
            .catch(err => setError(err.message));
    }, []);

    async function selectSheet(sheet) {
        setActiveSheet(sheet);
        setSheetData(null);
        setLoading(true);
        setError('');
        try {
            const data = await getSheetData(token, sheet.id);
            setSheetData(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

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
                            className={`sidebar-item ${activeSheet?.id === sheet.id ? 'active' : ''}`}
                            onClick={() => selectSheet(sheet)}
                        >
                            {sheet.display_name || sheet.name}
                        </button>
                    ))}
                </nav>

                <main className="dashboard-main">
                    {error && <p className="dash-error">{error}</p>}
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
                </main>
            </div>
        </div>
    );
}
