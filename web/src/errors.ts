import { t } from '@shared/i18n';

/** Any error from the API (or the network) -> a clear title and reason in French, never a raw "Request failed with status code 500". */
export function friendlyError(e: unknown): { title: string; why: string } {
  const x = e as { code?: string; message?: string; response?: { status?: number } } | null;
  const st = x?.response?.status;
  const k = !x?.response && (x?.code === 'ERR_NETWORK' || /network/i.test(x?.message ?? '')) ? 'network'
    : x?.code === 'ECONNABORTED' || /timeout/i.test(x?.message ?? '') ? 'timeout'
    : st === 429 ? 'busy' : st === 404 ? 'notfound' : st && st >= 500 ? 'server' : 'unknown';
  return { title: t(`errs.${k}.title`), why: t(`errs.${k}.why`) };
}
