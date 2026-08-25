export interface HistoricalCaseMedia {
  sourceType: 'CASE_SOURCE_MEDIA'
  sourcePage: string
  urls: string[]
}

// These URLs are direct images identified in the RC2.3 research manifest.
// No third-party media is downloaded or checked into the repository here.
export const HISTORICAL_CASE_MEDIA: Record<string, HistoricalCaseMedia> = {
  'SH-FLOOD-2023-0722-HK-01': {
    sourceType: 'CASE_SOURCE_MEDIA',
    sourcePage: 'https://www.shhk.gov.cn/xwzx/002008/002008040/20230723/d0990120-097d-455a-b9fd-4e72db0be6ec.html',
    urls: [
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/7b8217ad-bc26-42ee-986a-dedd28cd69ed/20230723112754004249.png',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/8e63306c-19ee-48ce-9ed5-1ae3ef405a66/20230723112750091185.jpg',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/4015999e-c6fd-496c-adaa-3f538026b3ac/20230723112746042712.jpg',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/960d0e00-04a7-44ba-bbbe-5c54da8c8a2a/20230723112742070370.jpg',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/780e5a6e-0bd4-4f95-9438-fb084042be90/20230723112739057036.jpg',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/e7647c09-2dcb-4328-91b6-1ebc3393a1b7/20230723112734051883.jpg',
      'https://www.shhk.gov.cn/shhk/d0990120-097d-455a-b9fd-4e72db0be6ec/7061a80f-d3ae-4e6c-9b3d-201000d81a53/20230723112728083896.jpg',
    ],
  },
  'SH-FLOOD-2025-0730-HK-01': {
    sourceType: 'CASE_SOURCE_MEDIA',
    sourcePage: 'https://www.shhk.gov.cn/xwzx/002003/20250801/7d0094ff-fa71-47f8-babd-ac92f37e0aa3.html',
    urls: [
      'https://www.shhk.gov.cn/shhk/7d0094ff-fa71-47f8-babd-ac92f37e0aa3/3b1d317a-6dbd-4559-ba45-44d2111e4ba8/image.png',
      'https://www.shhk.gov.cn/shhk/7d0094ff-fa71-47f8-babd-ac92f37e0aa3/23e0de4c-42d6-4027-b07a-64a93871cf34/image.png',
      'https://www.shhk.gov.cn/shhk/7d0094ff-fa71-47f8-babd-ac92f37e0aa3/430329e3-cc60-4d27-8565-fd2895fdce32/image.png',
      'https://www.shhk.gov.cn/shhk/7d0094ff-fa71-47f8-babd-ac92f37e0aa3/4fe41363-988a-415c-9b25-a29e0b8f30a3/image.png',
      'https://www.shhk.gov.cn/shhk/7d0094ff-fa71-47f8-babd-ac92f37e0aa3/5ced6b33-a5cc-48c3-a562-f29de4aa69d3/image.png',
    ],
  },
}

export function getHistoricalCaseMedia(candidateId: string): HistoricalCaseMedia | null {
  return HISTORICAL_CASE_MEDIA[candidateId] ?? null
}
