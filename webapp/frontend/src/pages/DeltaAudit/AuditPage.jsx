import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useAudit } from '../../hooks/useAudit';
import { useModelGovernance } from '../../hooks/useModelGovernance';
import TimeTravelSnapshot from './components/TimeTravelSnapshot';
import CommitHistoryTable from './components/CommitHistoryTable';
import SnapshotSampleRecords from './components/SnapshotSampleRecords';
import DeltaUnavailableNotice from './components/DeltaUnavailableNotice';

// The backend may return `detail` as a string or as an object ({ error, message }).
function errorText(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return detail.message || detail.error || JSON.stringify(detail);
  return err?.message || 'Unknown error';
}

export default function AuditPage() {
  const { user } = useAuth();
  const { getTimeTravel, getCommits, rerunEval } = useAudit();
  const { getRegistry } = useModelGovernance();

  const [commits, setCommits] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [loadedVersion, setLoadedVersion] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [commitsLoading, setCommitsLoading] = useState(true);
  const [commitsError, setCommitsError] = useState(null);
  const [modelRegistryMap, setModelRegistryMap] = useState({});

  const [rerunLoading, setRerunLoading] = useState(false);
  const [rerunResult, setRerunResult] = useState(null);
  const [forceRecompute, setForceRecompute] = useState(false);

  // Commit history pagination
  const [historyPage, setHistoryPage] = useState(1);
  const historyPerPage = 15;

  const abortControllerRef = useRef(null);

  // Loads one snapshot. On failure nothing is invented: the error is shown and the data is cleared.
  const executeLoad = useCallback(async (v) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setLoadError(null);
    setRerunResult(null);

    try {
      const data = await getTimeTravel(v, {
        signal: abortControllerRef.current.signal,
      });
      setAuditData(data);
      setLoadedVersion(data.version !== undefined && data.version !== null ? data.version : v);

      if (Array.isArray(data.commit_history) && data.commit_history.length > 0) {
        setCommits(data.commit_history);
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        return;
      }
      setLoadError(errorText(err));
      setAuditData(null);
      setLoadedVersion(null);
    } finally {
      setLoading(false);
    }
  }, [getTimeTravel]);

  useEffect(() => {
    let isMounted = true;

    getCommits(145)
      .then((data) => {
        if (!isMounted) return;
        const list = Array.isArray(data) ? data : [];
        setCommits(list);
        setCommitsError(null);
        setCommitsLoading(false);
        if (list.length > 0) {
          const latestVer = list[0].version;
          setSelectedVersion(latestVer);
          executeLoad(latestVer);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Error loading Delta commit history:', err);
        setCommitsError(errorText(err));
        setCommitsLoading(false);
      });

    getRegistry()
      .then((data) => {
        if (!isMounted) return;
        const map = {};
        if (Array.isArray(data?.models)) {
          data.models.forEach((m) => {
            if (m.gold_delta_version !== undefined && m.gold_delta_version !== null) {
              map[m.gold_delta_version] = m;
            }
          });
        }
        setModelRegistryMap(map);
      })
      .catch(() => {});

    return () => {
      isMounted = false;
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [executeLoad, getCommits, getRegistry]);

  const handleManualLoad = () => {
    if (selectedVersion !== null && selectedVersion !== undefined) {
      executeLoad(Number(selectedVersion));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleManualLoad();
    }
  };

  const handleRerun = async () => {
    const v = loadedVersion ?? selectedVersion;
    if (v === null || v === undefined) return;
    setRerunLoading(true);
    setRerunResult(null);
    try {
      const data = await rerunEval(v, { force_recompute: forceRecompute });
      setRerunResult(data);
    } catch (e) {
      if (e?.response?.status === 409) {
        alert('An audit evaluation task is currently executing on the cluster. Please wait for completion.');
      } else {
        alert(`Error during re-evaluation: ${errorText(e)}`);
      }
    } finally {
      setRerunLoading(false);
    }
  };

  // An outage must never look like "0 commits": the failed lists are replaced by an explicit notice.
  const snapshotError = loadError || commitsError;
  const showHistoryNotice = commitsLoading || Boolean(commitsError) || (commits.length === 0 && Boolean(loadError));
  const showSamplesNotice = commitsLoading || (Boolean(loadError) && !auditData);

  const commitHistory = auditData?.commit_history || commits;
  const sampleData = auditData?.sample_data || [];

  const totalCommitsCount = commitHistory.length;
  const totalPages = Math.max(1, Math.ceil(totalCommitsCount / historyPerPage));
  const currentCommits = commitHistory.slice(
    (historyPage - 1) * historyPerPage,
    historyPage * historyPerPage,
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <TimeTravelSnapshot
        selectedVersion={selectedVersion}
        setSelectedVersion={setSelectedVersion}
        loadedVersion={loadedVersion}
        commits={commits}
        modelRegistryMap={modelRegistryMap}
        handleManualLoad={handleManualLoad}
        handleKeyDown={handleKeyDown}
        loading={loading}
        loadError={snapshotError}
        auditData={auditData}
        user={user}
        forceRecompute={forceRecompute}
        setForceRecompute={setForceRecompute}
        handleRerun={handleRerun}
        rerunLoading={rerunLoading}
        rerunResult={rerunResult}
      />

      {showHistoryNotice ? (
        <DeltaUnavailableNotice subject="Commit history" reason={commitsError || loadError} loading={commitsLoading} />
      ) : (
        <CommitHistoryTable
          currentCommits={currentCommits}
          totalCommitsCount={totalCommitsCount}
          auditData={auditData}
          historyPage={historyPage}
          setHistoryPage={setHistoryPage}
          totalPages={totalPages}
          loadedVersion={loadedVersion}
          loading={loading}
        />
      )}

      {showSamplesNotice ? (
        <DeltaUnavailableNotice subject="Sample records" reason={loadError || commitsError} loading={commitsLoading} />
      ) : (
        <SnapshotSampleRecords
          sampleData={sampleData}
          loading={loading}
          loadedVersion={loadedVersion}
          selectedVersion={selectedVersion}
        />
      )}
    </div>
  );
}
