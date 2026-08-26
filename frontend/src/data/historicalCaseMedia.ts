import historicalCasesFixture from '../../../data/historical-cases.json'
import type { HistoricalCaseMedia as HistoricalCaseMediaType } from '../types'

export type HistoricalCaseMedia = HistoricalCaseMediaType

type HistoricalCaseWithMedia = { candidateId: string; media?: HistoricalCaseMedia | null }

const mediaByCandidate = Object.fromEntries(
  (historicalCasesFixture.records as HistoricalCaseWithMedia[])
    .filter((item) => item.media?.sourceType === 'CASE_SOURCE_MEDIA')
    .map((item) => [item.candidateId, item.media as HistoricalCaseMedia]),
)

export function getHistoricalCaseMedia(candidateId: string): HistoricalCaseMedia | null {
  return mediaByCandidate[candidateId] ?? null
}
