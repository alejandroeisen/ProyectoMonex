import { useState, useMemo } from 'react';
import './DataTable.css';

export default function DataTable({ sheet, rows }) {
    const [filter, setFilter] = useState('');
    const [sortKey, setSortKey] = useState(null);
    const [sortDir, setSortDir] = useState('asc');

    const columns = sheet.columns || [];

    const filteredRows = useMemo(() => {
        const term = filter.toLowerCase();
        if (!term) return rows;
        return rows.filter(row =>
            Object.values(row).some(v =>
                v !== null && String(v).toLowerCase().includes(term)
            )
        );
    }, [rows, filter]);

    const sortedRows = useMemo(() => {
        if (!sortKey) return filteredRows;
        return [...filteredRows].sort((a, b) => {
            const av = a[sortKey] ?? '';
            const bv = b[sortKey] ?? '';
            if (av < bv) return sortDir === 'asc' ? -1 : 1;
            if (av > bv) return sortDir === 'asc' ? 1 : -1;
            return 0;
        });
    }, [filteredRows, sortKey, sortDir]);

    function toggleSort(col) {
        if (sortKey === col) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(col);
            setSortDir('asc');
        }
    }

    function sortIndicator(col) {
        if (sortKey !== col) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon active">{sortDir === 'asc' ? '↑' : '↓'}</span>;
    }

    const lastSynced = sheet.last_synced_at
        ? new Date(sheet.last_synced_at).toLocaleString()
        : 'Nunca';

    return (
        <div className="table-container">
            <div className="table-toolbar">
                <div>
                    <h2 className="table-title">{sheet.display_name || sheet.name}</h2>
                    <p className="table-meta">
                        {sortedRows.length} of {rows.length} rows &nbsp;·&nbsp; Last synced: {lastSynced}
                    </p>
                </div>
                <input
                    className="table-search"
                    type="text"
                    placeholder="Buscar..."
                    value={filter}
                    onChange={e => setFilter(e.target.value)}
                />
            </div>

            {columns.length === 0 ? (
                <p className="table-empty">No columns found.</p>
            ) : (
                <div className="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                {columns.map(col => (
                                    <th key={col} onClick={() => toggleSort(col)}>
                                        {col} {sortIndicator(col)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sortedRows.length === 0 ? (
                                <tr>
                                    <td colSpan={columns.length} className="no-results">
                                        No rows match your search.
                                    </td>
                                </tr>
                            ) : (
                                sortedRows.map((row, i) => (
                                    <tr key={i}>
                                        {columns.map(col => (
                                            <td key={col}>
                                                {row[col] !== null && row[col] !== undefined
                                                    ? String(row[col])
                                                    : '—'}
                                            </td>
                                        ))}
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
