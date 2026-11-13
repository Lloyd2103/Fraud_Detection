import { useState, useCallback } from 'react';
import { healthApi } from '../api';

export function useHealth() {
  const [pipelineState, setPipelineState] = useState({
    kafkaActive: true,
    pipelineDown: false,
    lastAlertText: 'checking...',
  });

  const checkPipelineHealth = useCallback(async () => {
    try {
      const res = await healthApi.fetchPipelineHealth();
      const data = res.data;
      const kafkaReachable = Boolean(data.kafka_reachable);
      const isDown = !kafkaReachable || data.detector_state === 'DOWN';

      let lastText = 'active';
      if (data.last_alert_age_seconds !== null && data.last_alert_age_seconds !== undefined) {
        const secs = data.last_alert_age_seconds;
        if (secs < 60) {
          lastText = 'just now';
        } else if (secs < 3600) {
          lastText = `${Math.floor(secs / 60)}m ago`;
        } else if (secs < 86400) {
          lastText = `${Math.floor(secs / 3600)}h ago`;
        } else {
          lastText = `${Math.floor(secs / 86400)}d ago`;
        }
      }

      setPipelineState({
        kafkaActive: kafkaReachable,
        pipelineDown: isDown,
        lastAlertText: isDown ? `Pipeline: DOWN (last alert ${lastText})` : 'Pipeline: ACTIVE',
        detectorState: data.detector_state,
      });
      return data;
    } catch (_) {
      setPipelineState((prev) => ({
        ...prev,
        pipelineDown: true,
        lastAlertText: 'Pipeline: UNREACHABLE',
      }));
      return null;
    }
  }, []);

  return {
    pipelineState,
    checkPipelineHealth,
    fetchHealth: healthApi.fetchHealth,
    fetchPipelineHealth: healthApi.fetchPipelineHealth,
  };
}

export default useHealth;

