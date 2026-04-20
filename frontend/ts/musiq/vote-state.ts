import {localStorageGet, localStorageSet} from '../base';

const DEFAULT_VOTE_TTL_DAYS = 7;

type RuntimeWindow = Window & {
  RUNTIME_INSTANCE_ID?: string,
};

function voteNamespace(): string {
  const runtimeWindow = window as RuntimeWindow;
  const runtimeId = (runtimeWindow.RUNTIME_INSTANCE_ID || '').trim() || 'unknown-runtime';
  return 'vote-state-' + runtimeId + '-';
}

function normalizeQueueKey(queueKey: number | string): number {
  return Number(queueKey);
}

export function getStoredVote(queueKey: number | string): string | null {
  const normalizedKey = normalizeQueueKey(queueKey);
  if (!Number.isFinite(normalizedKey) || normalizedKey <= 0) {
    return null;
  }
  return localStorageGet(voteNamespace() + normalizedKey);
}

export function setStoredVote(
    queueKey: number | string,
    value: string,
    ttlDays = DEFAULT_VOTE_TTL_DAYS) {
  const normalizedKey = normalizeQueueKey(queueKey);
  if (!Number.isFinite(normalizedKey) || normalizedKey <= 0) {
    return;
  }
  localStorageSet(voteNamespace() + normalizedKey, value, ttlDays);
}
